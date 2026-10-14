import 'package:chosung/api/api_models.dart';
import 'package:chosung/puzzle/board_layout.dart';
import 'package:flutter/foundation.dart';

/// 온보딩 1·2장에 그려지는 예시 보드. 진짜 퍼즐이 아니라 **설명용 그림**이라
/// 서버를 부르지 않는다 — 첫 실행에 네트워크가 느리면 규칙 설명부터 비어
/// 보이고, 그 날 퍼즐을 미리 보여주면 정답 글자 수가 새어 나간다.
@immutable
class OnboardingSample {
  const OnboardingSample({required this.mask, required this.attempt});

  /// 1장 "하루 한 문제" 의 가림 행.
  final List<BoardCell> mask;

  /// 2장 "5번의 기회" 의 시도 행 — 맞은 자리와 아닌 자리가 섞여 있다.
  final List<BoardCell> attempt;
}

/// 고른 퍼즐 언어의 예시. 칩을 누르면 그림이 바로 그 언어로 바뀌어서,
/// "영어를 고르면 뭐가 나오는지" 를 글이 아니라 타일로 보여준다.
OnboardingSample onboardingSample(PuzzleLanguage language) =>
    switch (language) {
      // 지하철역 ← 지하주차: 앞 두 글자만 자리까지 맞았다.
      PuzzleLanguage.ko => const OnboardingSample(
        mask: [
          BoardCell(BoardCellKind.letter, 'ㅈ'),
          BoardCell(BoardCellKind.letter, 'ㅎ'),
          BoardCell(BoardCellKind.letter, 'ㅊ'),
          BoardCell(BoardCellKind.letter, 'ㅇ'),
        ],
        attempt: [
          BoardCell(BoardCellKind.correct, '지'),
          BoardCell(BoardCellKind.correct, '하'),
          BoardCell(BoardCellKind.wrong, '주'),
          BoardCell(BoardCellKind.wrong, '차'),
        ],
      ),
      // APPLE ← APPLY: 모음 자리는 빈 타일로 둔다(OVERRIDES §3).
      PuzzleLanguage.en => const OnboardingSample(
        mask: [
          BoardCell.empty,
          BoardCell(BoardCellKind.letter, 'P'),
          BoardCell(BoardCellKind.letter, 'P'),
          BoardCell(BoardCellKind.letter, 'L'),
          BoardCell.empty,
        ],
        attempt: [
          BoardCell(BoardCellKind.correct, 'A'),
          BoardCell(BoardCellKind.correct, 'P'),
          BoardCell(BoardCellKind.correct, 'P'),
          BoardCell(BoardCellKind.correct, 'L'),
          BoardCell(BoardCellKind.wrong, 'Y'),
        ],
      ),
    };
