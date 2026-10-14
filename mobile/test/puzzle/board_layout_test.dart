import 'package:chosung/api/api_models.dart';
import 'package:chosung/puzzle/board_layout.dart';
import 'package:flutter_test/flutter_test.dart';

/// ko "지하철역" 의 가림 — 초성 4개가 전부 보이는 타일이다.
const _koMask = [
  MaskTile(type: MaskTileType.revealed, char: 'ㅈ'),
  MaskTile(type: MaskTileType.revealed, char: 'ㅎ'),
  MaskTile(type: MaskTileType.revealed, char: 'ㅊ'),
  MaskTile(type: MaskTileType.revealed, char: 'ㅇ'),
];

/// en "Red Fox" 의 가림 — 모음이 빈 타일, 공백이 구분자다.
const _enMask = [
  MaskTile(type: MaskTileType.revealed, char: 'R'),
  MaskTile(type: MaskTileType.hidden, char: ''),
  MaskTile(type: MaskTileType.revealed, char: 'D'),
  MaskTile(type: MaskTileType.separator, char: ' '),
  MaskTile(type: MaskTileType.revealed, char: 'F'),
  MaskTile(type: MaskTileType.hidden, char: ''),
  MaskTile(type: MaskTileType.revealed, char: 'X'),
];

void main() {
  group('maskCells', () {
    test('보이는 타일은 글자, 빈 타일은 글자 없음', () {
      final cells = maskCells(_koMask);

      expect(cells.map((cell) => cell.kind), [
        BoardCellKind.letter,
        BoardCellKind.letter,
        BoardCellKind.letter,
        BoardCellKind.letter,
      ]);
      expect(cells.map((cell) => cell.char).join(), 'ㅈㅎㅊㅇ');
    });

    test('en 의 구분자는 타일이 아니라 간격이다', () {
      final cells = maskCells(_enMask);

      expect(cells.map((cell) => cell.kind), [
        BoardCellKind.letter,
        BoardCellKind.empty,
        BoardCellKind.letter,
        BoardCellKind.gap,
        BoardCellKind.letter,
        BoardCellKind.empty,
        BoardCellKind.letter,
      ]);
      // 빈 타일은 정답 글자를 들고 있지 않다.
      expect(cells[1].char, isEmpty);
    });
  });

  group('attemptCells', () {
    test('피드백대로 correct/wrong 타일이 된다', () {
      final cells = attemptCells(
        _koMask,
        const PuzzleAttempt(
          guess: '지하촌역',
          feedback: [true, false, false, true],
        ),
      );

      expect(cells.map((cell) => cell.kind), [
        BoardCellKind.correct,
        BoardCellKind.wrong,
        BoardCellKind.wrong,
        BoardCellKind.correct,
      ]);
      expect(cells.map((cell) => cell.char).join(), '지하촌역');
    });

    // 미정 13: 서버는 구분자를 뺀 글자열만 저장한다. 보드를 복원할 때
    // `mask` 의 `s` 위치에 간격을 다시 끼워 문제 행과 시도 행이 맞게 한다.
    test('en 시도 행은 mask 의 `s` 자리에 간격을 다시 끼운다', () {
      final cells = attemptCells(
        _enMask,
        const PuzzleAttempt(
          guess: 'REDFOX',
          feedback: [true, true, true, true, false, true],
        ),
      );

      expect(cells.map((cell) => cell.kind), [
        BoardCellKind.correct,
        BoardCellKind.correct,
        BoardCellKind.correct,
        BoardCellKind.gap,
        BoardCellKind.correct,
        BoardCellKind.wrong,
        BoardCellKind.correct,
      ]);
      // 간격은 글자를 안 먹는다 — 4번째 글자 F 가 공백 뒤 첫 타일이다.
      expect(cells[4].char, 'F');
      expect(cells[3].char, isEmpty);
    });

    // 구분자 규칙이 지금과 달랐던 옛 행도 그려야 한다(서버 compare_letters 가
    // 짧은 guess 를 빈칸으로 채우는 것과 같은 이유다).
    test('글자 수가 모자란 옛 행은 빈 타일로 채운다', () {
      final cells = attemptCells(
        _koMask,
        const PuzzleAttempt(guess: '지하', feedback: [true, true, false, false]),
      );

      expect(cells.map((cell) => cell.kind), [
        BoardCellKind.correct,
        BoardCellKind.correct,
        BoardCellKind.empty,
        BoardCellKind.empty,
      ]);
    });
  });

  group('emptyRowCells', () {
    test('아직 안 쓴 행도 같은 간격을 쓴다', () {
      final cells = emptyRowCells(_enMask);

      expect(cells.map((cell) => cell.kind), [
        BoardCellKind.empty,
        BoardCellKind.empty,
        BoardCellKind.empty,
        BoardCellKind.gap,
        BoardCellKind.empty,
        BoardCellKind.empty,
        BoardCellKind.empty,
      ]);
    });
  });

  group('tileSize', () {
    // OVERRIDES §4: 48(5글자 이하) / 40(6~8글자) / 9글자+ 는 줄바꿈.
    test('글자 수에 따라 48 또는 40 이다', () {
      expect(tileSize(4), 48.0);
      expect(tileSize(5), 48.0);
      expect(tileSize(6), 40.0);
      expect(tileSize(8), 40.0);
      expect(tileSize(12), 40.0);
    });
  });
}
