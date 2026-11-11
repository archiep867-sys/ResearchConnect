import csv

import pytest

from algorithms import analytics, data_manager


@pytest.fixture
def dataset_factory(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, 'DATA_DIR', str(tmp_path))

    def make(papers):
        for filename, fields, rows in [
            ('faculty.csv', data_manager.FACULTY_COLUMNS,
             [{'faculty_id': 'f1', 'expertise': 'Expertise only'}]),
            ('papers.csv', data_manager.PAPER_COLUMNS, papers),
            ('authorship.csv', data_manager.AUTHORSHIP_COLUMNS, []),
        ]:
            with (tmp_path / filename).open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        return data_manager.Dataset()

    return make


def test_exact_labels_and_matrix(dataset_factory):
    ds = dataset_factory([
        {'paper_id': 'p1', 'year': '2024', 'keywords': 'Vision; AI; ai; IoT; IOT'},
        {'paper_id': 'p2', 'year': '2025', 'keywords': 'iot; Ai; ai'},
        {'paper_id': 'single', 'year': '2025', 'keywords': 'Robotics; robotics'},
        {'paper_id': 'missing_year', 'keywords': 'AI; vision; VISION'},
    ])
    result = analytics.keyword_cooccurrence(ds)
    assert result == {
        'labels': ['AI', 'IoT', 'Robotics', 'Vision'],
        'matrix': [
            [0, 2, 0, 2],
            [2, 0, 0, 1],
            [0, 0, 0, 0],
            [2, 1, 0, 0],
        ],
    }
    matrix = result['matrix']
    for i in range(len(result['labels'])):
        assert len(matrix[i]) == len(result['labels'])
        assert matrix[i][i] == 0
        for j in range(len(result['labels'])):
            assert matrix[i][j] == matrix[j][i]
            assert type(matrix[i][j]) is int


def test_normalized_order_before_display_labels(dataset_factory):
    ds = dataset_factory([{'paper_id': 'p1', 'keywords': 'AI; IoT'}])
    ds.keyword_labels.update({'ai': 'zAI', 'iot': 'aIoT'})
    assert analytics.keyword_cooccurrence(ds) == {
        'labels': ['zAI', 'aIoT'], 'matrix': [[0, 1], [1, 0]],
    }


def test_single_keyword_paper(dataset_factory):
    ds = dataset_factory([{'paper_id': 'single', 'keywords': 'Robotics; ROBOTICS'}])
    assert analytics.keyword_cooccurrence(ds) == {'labels': ['Robotics'], 'matrix': [[0]]}


@pytest.mark.parametrize('year', ['', 'invalid'])
def test_year_does_not_exclude_pairs(dataset_factory, year):
    ds = dataset_factory([{'paper_id': 'p1', 'year': year, 'keywords': 'IoT; AI'}])
    assert ds.papers[0]['year_num'] is None
    assert analytics.keyword_cooccurrence(ds) == {
        'labels': ['AI', 'IoT'], 'matrix': [[0, 1], [1, 0]],
    }


@pytest.mark.parametrize('papers', [
    [],
    [{'paper_id': 'blank', 'year': '2024', 'keywords': ''}],
])
def test_no_paper_keywords(dataset_factory, papers):
    assert analytics.keyword_cooccurrence(dataset_factory(papers)) == {'labels': [], 'matrix': []}
