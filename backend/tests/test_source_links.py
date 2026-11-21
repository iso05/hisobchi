from app.catalog import CATALOG, LAW, EPOWER_SOURCE, working_source_url, exact_source_url, precise_result_sources


def test_catalog_sources_use_native_document_anchors():
    for service in CATALOG:
        for source in service['sources']:
            base, anchor = source['url'].split('#')
            assert base in {LAW, EPOWER_SOURCE}
            assert anchor.split(':~:text=')[0].startswith('-') and anchor.split(':~:text=')[0][1:].isdigit()
            assert ':~:text=' in anchor
            assert source['find_text']


def test_legacy_generated_links_resolve_but_other_versions_are_retained():
    assert working_source_url(LAW + '?ONDATE=20.11.2026#:~:text=p%29%20avtomototransport') == exact_source_url(LAW, 'p) avtomototransport')
    assert working_source_url(EPOWER_SOURCE + '?ONDATE=20.11.2026#:~:text=15.%20Ishonchnomani') == exact_source_url(EPOWER_SOURCE, '15. Ishonchnomani')
    assert working_source_url(LAW + '#:~:text=p%29%20avtomototransport') == exact_source_url(LAW, 'p) avtomototransport')
    historic = LAW + '?ONDATE=01.01.2020'
    assert working_source_url(historic) == historic


def test_duplicate_admin_source_keeps_one_precise_link():
    known = CATALOG[2]['sources'][0]
    old = {'article': known['article'], 'url': LAW + '#-8113528'}
    resolved = precise_result_sources('notary_vehicle_power', [known, old])
    assert len(resolved) == 1
    assert resolved[0]['find_text'] == known['find_text']
    assert ':~:text=' in resolved[0]['url']
