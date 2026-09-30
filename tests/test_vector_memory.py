import pytest
from deer.memory import VectorMemory


@pytest.fixture
def temp_memory(tmp_path):
    """
    Creates a VectorMemory instance in a unique temporary directory
    provided by pytest's tmp_path fixture. This prevents
    'readonly database' errors caused by file locking.
    """
    # Create a unique subdirectory for this specific test
    db_dir = tmp_path / "vector_db"
    db_dir.mkdir()

    # Pass the absolute string path to the memory class
    memory = VectorMemory(path=db_dir)
    return memory


def test_add_and_query(temp_memory):
    """
    Tests that a document can be added and retrieved.

    Parameters
    ----------
    temp_memory : VectorMemory
        The temporary memory instance provided by the fixture.
    """
    doc_id = "test_1"
    text = "The sky is blue and the sun is yellow"

    temp_memory.add_document(doc_id, text)
    results = temp_memory.query("color of the sky")

    assert len(results) > 0
    assert results[0]["id"] == doc_id
    assert "blue" in results[0]["text"]


def test_hit_count_increment(temp_memory):
    """
    Tests that hit_count is automatically incremented upon querying.

    Parameters
    ----------
    temp_memory : VectorMemory
        The temporary memory instance provided by the fixture.
    """
    doc_id = "test_hit"
    temp_memory.add_document(doc_id, "Persistent information")

    # Query 3 times
    for _ in range(3):
        temp_memory.query("Information")

    # Verify counter via audit
    audit = temp_memory.audit_full_memory()
    hit_count = next(item["hit_count"] for item in audit if item["id"] == doc_id)

    assert hit_count == 3


def test_clear_unused_documents(temp_memory):
    """
    Tests that only documents with hit_count == 0 are deleted.

    Parameters
    ----------
    temp_memory : VectorMemory
        The temporary memory instance provided by the fixture.
    """
    temp_memory.add_document("used", "This one is used")
    temp_memory.add_document("unused", "This one is not used")

    # Query only the first one
    temp_memory.query("used", n_results=1)

    deleted_count = temp_memory.clear_unused_documents()

    assert deleted_count == 1
    assert temp_memory.collection.count() == 1

    # Verify the correct one remains
    remaining = temp_memory.collection.get()
    assert "used" in remaining["ids"]


def test_shrink_to_size(temp_memory):
    """
    Tests that aggressive cleanup reduces the DB to the target size.

    Parameters
    ----------
    temp_memory : VectorMemory
        The temporary memory instance provided by the fixture.
    """
    # Add a very heavy document and a light one
    temp_memory.add_document("popular_light", "Short")
    temp_memory.add_document("unpopular_heavy", "Long " * 20000)

    # Make the light one popular
    temp_memory.query("Short", n_results=1)

    # Target a very small size to force deletion of the heavy doc
    # temp_memory.shrink_to_size("10 KB")
    temp_memory.shrink_to_size("10 KB")

    remaining_ids = temp_memory.collection.get()["ids"]
    assert "popular_light" in remaining_ids
    assert "unpopular_heavy" not in remaining_ids


def test_get_db_info(temp_memory):
    """
    Tests that DB information is consistent.

    Parameters
    ----------
    temp_memory : VectorMemory
        The temporary memory instance provided by the fixture.
    """
    temp_memory.add_document("id1", "Text 1")
    temp_memory.add_document("id2", "Text 2")

    info = temp_memory.get_db_info()

    assert info["total_documents"] == 2
    assert info["disk_size_bytes"] > 0
