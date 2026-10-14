import 'package:chosung/api/api_models.dart';
import 'package:flutter/foundation.dart';

/// 보드 한 칸이 그려지는 모양. 색은 화면이 토큰에서 고른다(OVERRIDES §2).
enum BoardCellKind {
  /// 문제 행의 보이는 타일(ko 초성, en 자음).
  letter,

  /// 아직 안 쓴 칸(`tile-empty`). 문제 행의 빈 타일도 같은 모양이다.
  empty,

  /// 타일이 아니라 타일 사이 간격 — `mask` 의 `s`.
  gap,

  /// 위치·글자 일치(`tile-correct`).
  correct,

  /// 불일치(`tile-wrong`).
  wrong
  ;

  bool get isGap => this == gap;
}

@immutable
class BoardCell {
  const BoardCell(this.kind, [this.char = '']);

  static const gap = BoardCell(BoardCellKind.gap);
  static const empty = BoardCell(BoardCellKind.empty);

  final BoardCellKind kind;
  final String char;
}

/// 문제 행. 빈 타일은 글자를 들고 있지 않다 — 서버도 `c` 를 비워 보낸다.
List<BoardCell> maskCells(List<MaskTile> mask) => [
  for (final tile in mask)
    switch (tile.type) {
      MaskTileType.revealed => BoardCell(BoardCellKind.letter, tile.char),
      MaskTileType.hidden => BoardCell.empty,
      MaskTileType.separator => BoardCell.gap,
    },
];

/// 제출한 행. **`mask` 를 따라 걸으면서 `s` 자리에 간격을 다시 끼운다** —
/// 서버 `Attempt.guess` 는 구분자를 뺀 글자열이라(스펙 "미정 항목" 13) 그냥
/// 그리면 en 보드의 시도 행이 문제 행과 한 칸씩 어긋난다.
List<BoardCell> attemptCells(List<MaskTile> mask, PuzzleAttempt attempt) {
  final cells = <BoardCell>[];
  var letter = 0;

  for (final tile in mask) {
    if (tile.type == MaskTileType.separator) {
      cells.add(BoardCell.gap);
      continue;
    }
    // 구분자 규칙이 지금과 달랐던 옛 행은 글자가 모자랄 수 있다. 서버
    // `compare_letters` 가 짧은 guess 를 빈칸으로 채우는 것과 같은 처리다.
    if (letter >= attempt.guess.length) {
      cells.add(BoardCell.empty);
    } else {
      final correct =
          letter < attempt.feedback.length && attempt.feedback[letter];
      cells.add(
        BoardCell(
          correct ? BoardCellKind.correct : BoardCellKind.wrong,
          attempt.guess[letter],
        ),
      );
    }
    letter++;
  }

  return cells;
}

/// 아직 안 쓴 행. 간격 자리가 같아야 문제 행과 세로로 맞는다.
List<BoardCell> emptyRowCells(List<MaskTile> mask) => [
  for (final tile in mask)
    tile.type == MaskTileType.separator ? BoardCell.gap : BoardCell.empty,
];

/// 타일 한 변의 길이(OVERRIDES §4). 9글자부터는 줄바꿈으로 넘긴다.
double tileSize(int length) => length <= 5 ? 48 : 40;
