from sqlmodel import select

from app.models.relational_entry import EntryModel, Resource


def test_entry_model_round_trips_through_sqlite(db_session):
    entry = EntryModel(
        id="lex_test-entry",
        lemma="test-entry",
        resource=Resource.BDO,
        original_id="orig-1",
        index_letter="t",
        language="de",
    )

    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)

    results = db_session.exec(select(EntryModel)).all()

    assert len(results) == 1

    result = results[0]

    assert result.lemma == "test-entry"
    assert result.resource == Resource.BDO
    assert result.original_id == "orig-1"
