from langchain_core.documents import Document

from conftest import fake_llm
from documind.memory import ConversationMemory
from documind.pipeline import NO_DOCS_MESSAGE, RAGPipeline, build_citations, cited_indices, format_context


def make_pipeline(settings, embeddings, llm=None):
    return RAGPipeline(settings, embeddings, llm=llm)


# ------------------------------------------------------------------ helpers
def test_cited_indices_order_and_bounds():
    assert cited_indices("A [2] B [1][2] C [9]", n_sources=3) == [2, 1]


def test_build_citations_falls_back_to_all_when_uncited():
    hits = [(Document("aaa", metadata={"source": "a.pdf", "page": 1}), 0.9),
            (Document("bbb", metadata={"source": "b.pdf", "page": 4}), 0.5)]
    assert [c.index for c in build_citations("no markers", hits)] == [1, 2]
    cites = build_citations("see [2]", hits)
    assert len(cites) == 1 and cites[0].file_name == "b.pdf" and cites[0].page == 4


def test_format_context_numbers_blocks():
    ctx = format_context([Document("x", metadata={"source": "a.pdf", "page": 3})])
    assert ctx.startswith("[1] (source: a.pdf, page 3)")


# ------------------------------------------------------------------ ingestion
def test_ingest_multiple_and_dedupe(settings, embeddings, solar_pdf, wind_pdf):
    p = make_pipeline(settings, embeddings)
    r1 = p.ingest_pdf(solar_pdf, "solar.pdf")
    r2 = p.ingest_pdf(wind_pdf, "wind.pdf")
    assert not r1.skipped and r1.pages == 2 and r1.chunks > 0
    assert not r2.skipped
    dup = p.ingest_pdf(solar_pdf, "solar-copy.pdf")
    assert dup.skipped and dup.reason == "already indexed"
    names = [f["file_name"] for f in p.store.list_files()]
    assert names == ["solar.pdf", "wind.pdf"]


def test_ingest_rejects_garbage(settings, embeddings):
    r = make_pipeline(settings, embeddings).ingest_pdf(b"%PDF-broken", "bad.pdf")
    assert r.skipped


def test_delete_file(settings, embeddings, solar_pdf, wind_pdf):
    p = make_pipeline(settings, embeddings)
    p.ingest_pdf(solar_pdf, "solar.pdf")
    p.ingest_pdf(wind_pdf, "wind.pdf")
    solar_hash = next(f["file_hash"] for f in p.store.list_files() if f["file_name"] == "solar.pdf")
    p.store.delete_file(solar_hash)
    assert [f["file_name"] for f in p.store.list_files()] == ["wind.pdf"]


def test_persistence_across_instances(settings, embeddings, solar_pdf):
    make_pipeline(settings, embeddings).ingest_pdf(solar_pdf, "solar.pdf")
    assert make_pipeline(settings, embeddings).store.count() > 0


# ------------------------------------------------------------------ retrieval
def test_semantic_search_finds_right_doc(settings, embeddings, solar_pdf, wind_pdf):
    p = make_pipeline(settings, embeddings)
    p.ingest_pdf(solar_pdf, "solar.pdf")
    p.ingest_pdf(wind_pdf, "wind.pdf")
    top_doc, _ = p.retrieve("offshore wind turbines")[0]
    assert top_doc.metadata["source"] == "wind.pdf"


def test_file_filter(settings, embeddings, solar_pdf, wind_pdf):
    p = make_pipeline(settings, embeddings)
    p.ingest_pdf(solar_pdf, "solar.pdf")
    p.ingest_pdf(wind_pdf, "wind.pdf")
    solar_hash = next(f["file_hash"] for f in p.store.list_files() if f["file_name"] == "solar.pdf")
    hits = p.retrieve("offshore wind turbines", file_hashes=[solar_hash])
    assert hits and all(d.metadata["source"] == "solar.pdf" for d, _ in hits)


# ------------------------------------------------------------------ answering + memory
def test_ask_returns_cited_sources_and_updates_memory(settings, embeddings, solar_pdf, wind_pdf):
    llm = fake_llm("Solar panels are 18–22% efficient [1].")
    p = make_pipeline(settings, embeddings, llm)
    p.ingest_pdf(solar_pdf, "solar.pdf")
    p.ingest_pdf(wind_pdf, "wind.pdf")
    mem = ConversationMemory(window=3)

    ans = p.ask("How efficient are solar panels?", mem)
    assert "[1]" in ans.answer
    assert len(ans.sources) == 1 and ans.sources[0].file_name == "solar.pdf"
    assert len(mem) == 1


def test_follow_up_is_condensed_using_history(settings, embeddings, solar_pdf):
    llm = fake_llm(
        "Panels convert sunlight [1].",                     # turn 1 answer
        "What is the main limitation of solar power?",      # condense rewrite
        "Intermittency at night [1].",                      # turn 2 answer
    )
    p = make_pipeline(settings, embeddings, llm)
    p.ingest_pdf(solar_pdf, "solar.pdf")
    mem = ConversationMemory(window=3)
    p.ask("How do solar panels work?", mem)
    ans = p.ask("What's its main limitation?", mem)
    assert ans.standalone_question == "What is the main limitation of solar power?"
    assert ans.sources[0].page == 2
    assert len(mem) == 2


def test_no_documents_message(settings, embeddings):
    p = make_pipeline(settings, embeddings, fake_llm("unused"))
    ans = p.ask("anything?", ConversationMemory())
    assert ans.answer == NO_DOCS_MESSAGE and ans.sources == []


def test_memory_window_slides():
    m = ConversationMemory(window=2)
    for i in range(5):
        m.add_turn(f"q{i}", f"a{i}")
    assert len(m) == 2
    assert [msg.content for msg in m.messages()] == ["q3", "a3", "q4", "a4"]
