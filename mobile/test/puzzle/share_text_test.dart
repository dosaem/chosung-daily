import 'package:chosung/api/api_models.dart';
import 'package:chosung/puzzle/share_text.dart';
import 'package:flutter_test/flutter_test.dart';

/// 웹(`web/static/app.js` 의 `buildShareText`)과 같은 포맷에 링크 한 줄만 더
/// 붙인다 — 같은 게임의 공유가 플랫폼마다 달라 보이지 않게.
void main() {
  group('maskShareText', () {
    test('빈 타일은 "_" 로 펼치고 구분자는 그대로 둔다', () {
      const mask = [
        MaskTile(type: MaskTileType.revealed, char: 'R'),
        MaskTile(type: MaskTileType.hidden, char: ''),
        MaskTile(type: MaskTileType.revealed, char: 'D'),
        MaskTile(type: MaskTileType.separator, char: ' '),
        MaskTile(type: MaskTileType.revealed, char: 'F'),
      ];

      expect(maskShareText(mask), 'R_D F');
    });
  });

  group('shareGrid', () {
    test('시도마다 한 줄, 맞은 칸은 🟩 틀린 칸은 ⬜', () {
      const attempts = [
        PuzzleAttempt(guess: '지하철역', feedback: [true, false, true, false]),
        PuzzleAttempt(guess: '지하철역', feedback: [true, true, true, true]),
      ];

      expect(shareGrid(attempts), '🟩⬜🟩⬜\n🟩🟩🟩🟩');
    });
  });

  group('buildShareText', () {
    test('머리글·문제·결과 + 빈 줄 + 그리드 + 빈 줄 + 링크 순서다', () {
      final text = buildShareText(
        heading: '오늘의 초성 2026-10-13',
        puzzleLine: 'ㅈㅎㅊㅇ (4글자)',
        resultLine: '2/5 성공',
        attempts: const [
          PuzzleAttempt(guess: '지하철역', feedback: [true, false, true, false]),
          PuzzleAttempt(guess: '지하철역', feedback: [true, true, true, true]),
        ],
      );

      expect(text, '''
오늘의 초성 2026-10-13
ㅈㅎㅊㅇ (4글자)
2/5 성공

🟩⬜🟩⬜
🟩🟩🟩🟩

$shareUrl''');
    });

    test('시도가 없으면 그리드 줄을 넣지 않는다', () {
      final text = buildShareText(
        heading: '오늘의 초성 2026-10-13',
        puzzleLine: 'ㅈㅎㅊㅇ (4글자)',
        resultLine: '5/5 실패',
        attempts: const [],
      );

      expect(text, '오늘의 초성 2026-10-13\nㅈㅎㅊㅇ (4글자)\n5/5 실패\n\n$shareUrl');
    });

    test('공유 링크에는 utm_source=share 가 붙는다(US 11)', () {
      expect(shareUrl, 'https://chosung.dosaem.com/?utm_source=share');
    });
  });

  group('shareDate', () {
    test('웹과 같은 ISO 날짜다 — 어디에 붙여도 같게 읽힌다', () {
      expect(shareDate(DateTime(2026, 10, 3)), '2026-10-03');
    });
  });
}
