"""`scripts/check_word_csv.py` — 올리기 전 로컬 검증 스크립트의 규칙 테스트.

실제 후보 파일(`data/word-candidates/*.csv`)은 커밋되지 않으므로 테스트가 읽지
않는다. 규칙만 임시 CSV 로 고정한다 — 파일이 없는 환경(CI)에서도 돌아야 한다.
DB 도 쓰지 않는다(스크립트가 `parse_word_input` 만 쓴다).
"""

import csv

import pytest

from scripts.check_word_csv import check_file, load_seed_keys, main

KO_HEADER = ("language", "category", "answer", "hint")


def write_csv(path, rows, header=KO_HEADER):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return str(path)


def reasons(path, seed_keys=frozenset()):
    return [f"{v.line}: {v.reason}" for v in check_file(path, seed_keys)]


def test_clean_ko_file_has_no_violations(tmp_path):
    path = write_csv(
        tmp_path / "ko.csv",
        [
            ("ko", "general", "책상", "공부할 때 앞에 두는 가구"),
            ("ko", "general", "우유", "젖소에게서 얻는 흰 음료"),
        ],
    )

    assert reasons(path) == []


def test_clean_en_file_has_no_violations(tmp_path):
    path = write_csv(
        tmp_path / "en.csv",
        [
            ("en", "general", "mountain", "a very tall landform"),
            ("en", "general", "ice cream", "a frozen sweet dessert"),
        ],
    )

    assert reasons(path) == []


def test_ko_hint_sharing_a_syllable_with_the_answer_is_caught(tmp_path):
    path = write_csv(
        tmp_path / "ko.csv",
        [("ko", "general", "책상", "책을 올려두는 가구")],
    )

    found = reasons(path)

    assert len(found) == 1
    assert found[0].startswith("2: ")
    assert "힌트" in found[0]
    assert "책" in found[0]


def test_en_hint_containing_the_answer_or_its_plural_is_caught(tmp_path):
    path = write_csv(
        tmp_path / "en.csv",
        [
            ("en", "general", "mountain", "a tall mountain of rock"),
            ("en", "general", "keyboard", "you type on keyboards"),
        ],
    )

    found = reasons(path)

    assert len(found) == 2
    assert all("힌트" in line for line in found)
    assert found[0].startswith("2: ")
    assert found[1].startswith("3: ")


def test_answer_longer_than_the_language_limit_is_caught(tmp_path):
    path = write_csv(
        tmp_path / "ko.csv",
        [
            ("ko", "general", "가나다라마바", "너무 긴 정답"),
            ("en", "general", "extraordinarily", "far too long for one tile row"),
        ],
    )

    found = reasons(path)

    assert len(found) == 2
    assert all("정답" in line for line in found)


def test_hint_longer_than_the_candidate_limit_is_caught(tmp_path):
    path = write_csv(
        tmp_path / "ko.csv",
        [("ko", "general", "책상", "앞에 두고 쓰는 " + "긴" * 60)],
    )

    found = reasons(path)

    assert len(found) == 1
    assert "힌트" in found[0]


def test_duplicate_answer_in_the_same_file_is_caught(tmp_path):
    path = write_csv(
        tmp_path / "ko.csv",
        [
            ("ko", "general", "우유", "젖소에게서 얻는 흰 음료"),
            ("ko", "general", "책상", "공부할 때 앞에 두는 가구"),
            ("ko", "general", "우유", "흰색 마실 것"),
        ],
    )

    found = reasons(path)

    assert len(found) == 1
    assert found[0].startswith("4: ")
    assert "중복" in found[0]


def test_unknown_category_is_caught_by_parse_word_input(tmp_path):
    path = write_csv(
        tmp_path / "ko.csv",
        [("ko", "noun", "책상", "공부할 때 앞에 두는 가구")],
    )

    found = reasons(path)

    assert len(found) == 1
    assert "category" in found[0]


def test_answer_already_in_seed_words_is_caught(tmp_path):
    path = write_csv(
        tmp_path / "ko.csv",
        [("ko", "general", "사과", "빨갛고 아삭한 열매")],
    )

    found = reasons(path, load_seed_keys("data/seed_words.csv"))

    assert len(found) == 1
    assert "seed_words.csv" in found[0]


def test_ko_answer_with_non_hangul_characters_is_caught(tmp_path):
    path = write_csv(
        tmp_path / "ko.csv",
        [
            ("ko", "general", "책 상", "공부할 때 앞에 두는 가구"),
            ("ko", "general", "ab우유", "젖소에게서 얻는 흰 음료"),
        ],
    )

    found = reasons(path)

    assert len(found) == 2
    assert all("정답" in line for line in found)


def test_en_answer_rules_catch_uppercase_extra_separators_and_vowel_heavy_words(tmp_path):
    path = write_csv(
        tmp_path / "en.csv",
        [
            ("en", "general", "Mountain", "a very tall landform"),
            ("en", "general", "a b c", "three letters in a row"),
            ("en", "general", "aeon", "a very long age"),
        ],
    )

    found = reasons(path)

    assert [line.split(":")[0] for line in found] == ["2", "3", "4"]
    assert "소문자" in found[0]
    assert "구분자" in found[1]
    assert "모음" in found[2]


def test_missing_header_column_is_reported_on_the_header_line(tmp_path):
    path = tmp_path / "ko.csv"
    write_csv(path, [("ko", "general", "책상")], header=("language", "category", "answer"))

    found = reasons(str(path))

    assert len(found) == 1
    assert found[0].startswith("1: ")
    assert "hint" in found[0]


def test_main_exits_zero_on_a_clean_file_and_one_on_violations(tmp_path, capsys):
    clean = write_csv(
        tmp_path / "clean.csv",
        [("ko", "general", "책상", "공부할 때 앞에 두는 가구")],
    )
    broken = write_csv(
        tmp_path / "broken.csv",
        [("ko", "general", "책상", "책을 올려두는 가구")],
    )

    assert main([clean]) == 0
    assert main([clean, broken]) == 1

    out = capsys.readouterr().out
    assert "broken.csv" in out
    assert "2: " in out


def test_main_reports_a_missing_file_instead_of_crashing(tmp_path, capsys):
    assert main([str(tmp_path / "nope.csv")]) == 1
    assert "nope.csv" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("answer", "hint"),
    [
        ("우유", ""),
        ("", "젖소에게서 얻는 흰 음료"),
    ],
)
def test_empty_answer_or_hint_is_caught(tmp_path, answer, hint):
    path = write_csv(tmp_path / "ko.csv", [("ko", "general", answer, hint)])

    assert len(reasons(path)) == 1


def test_header_names_with_stray_spaces_are_read_like_the_upload_does(tmp_path):
    """업로드(`missing_csv_columns`)가 공백을 무시하고 통과시키는 헤더다 — 여기서도
    같은 이름으로 읽어야 "로컬은 오류인데 업로드는 통과" 가 안 생긴다."""
    path = write_csv(
        tmp_path / "ko.csv",
        [("ko", "general", "책상", "공부할 때 앞에 두는 가구")],
        header=("language", " category", "answer ", "hint"),
    )

    assert reasons(path) == []
