from documind.activity import ActivityLog
from documind.ui.components import format_answer, human_size, workspace_label
from documind.ui.state import slugify_workspace


def test_activity_log_roundtrip_and_filters(tmp_path):
    log = ActivityLog(tmp_path, "Acme Legal")
    log.record("upload", "a.pdf", "3 pages")
    log.record("analysis", "What is X?", "2 references")
    log.record("upload", "b.pdf")
    events = log.events()
    assert [e.title for e in events] == ["b.pdf", "What is X?", "a.pdf"]  # newest first
    assert log.count("upload") == 2
    assert [e.title for e in log.events(kinds={"analysis"})] == ["What is X?"]
    assert events[0].label == "Document indexed"
    log.clear()
    assert log.events() == []


def test_workspace_slugs_are_valid_chroma_names():
    assert slugify_workspace("Acme Corp — Due Diligence") == "acme-corp-due-diligence"
    assert slugify_workspace("HR") == "hr-ws"
    assert workspace_label("acme-corp") == "Acme Corp"


def test_format_answer_escapes_html_and_styles_citations():
    out = format_answer("<script>x</script> Revenue rose 12% [2].")
    assert "<script>" not in out
    assert '<span class="dm-cite">2</span>' in out


def test_human_size():
    assert human_size(0) == "—"
    assert human_size(2048) == "2.0 KB"
