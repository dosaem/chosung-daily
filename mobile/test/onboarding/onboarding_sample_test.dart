import 'package:chosung/api/api_models.dart';
import 'package:chosung/onboarding/onboarding_sample.dart';
import 'package:chosung/puzzle/board_layout.dart';
import 'package:flutter_test/flutter_test.dart';

List<String> _kinds(List<BoardCell> cells) => [
  for (final cell in cells) cell.kind.name,
];

String _text(List<BoardCell> cells) => cells.map((cell) => cell.char).join();

void main() {
  group('ko 예시', () {
    final sample = onboardingSample(PuzzleLanguage.ko);

    test('1장은 초성 4칸이 모두 보이는 가림 행이다(목업 e6_onboarding)', () {
      expect(_text(sample.mask), 'ㅈㅎㅊㅇ');
      expect(_kinds(sample.mask), everyElement('letter'));
    });

    test('2장은 앞 두 칸만 맞은 시도 행이다', () {
      expect(_text(sample.attempt), '지하주차');
      expect(_kinds(sample.attempt), ['correct', 'correct', 'wrong', 'wrong']);
    });
  });

  group('en 예시', () {
    final sample = onboardingSample(PuzzleLanguage.en);

    // OVERRIDES §3: 영어 자음 뼈대의 빈칸은 언더스코어가 아니라 빈 타일이다.
    test('1장은 모음 자리가 빈 타일인 `_PPL_` 이다', () {
      expect(_kinds(sample.mask), [
        'empty',
        'letter',
        'letter',
        'letter',
        'empty',
      ]);
      expect(_text(sample.mask), 'PPL');
    });

    test('2장은 마지막 글자만 틀린 시도 행이다', () {
      expect(_text(sample.attempt), 'APPLY');
      expect(_kinds(sample.attempt), [
        'correct',
        'correct',
        'correct',
        'correct',
        'wrong',
      ]);
    });
  });
}
