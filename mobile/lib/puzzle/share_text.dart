import 'package:chosung/api/api_models.dart';
import 'package:easy_localization/easy_localization.dart';

/// 공유 텍스트에 붙는 웹 링크(US 11). `utm_source=share` 로 공유 유입을 센다.
const shareUrl = 'https://chosung.dosaem.com/?utm_source=share';

/// 공유 텍스트의 날짜. 웹(`web/static/app.js`)이 서버가 준 KST ISO 날짜를
/// 그대로 쓰므로 앱도 같은 형식이다 — 같은 날의 공유가 두 플랫폼에서 다르게
/// 읽히지 않게.
String shareDate(DateTime date) => DateFormat('yyyy-MM-dd').format(date);

/// 가림을 한 줄로 펼친다 — 빈 타일은 `_`, 구분자는 원래 글자(공백·하이픈).
/// 서버 `app/utils/mask.py` 의 `mask_to_text` 와 같은 자리표시자다.
String maskShareText(List<MaskTile> mask) => mask
    .map((tile) => tile.type == MaskTileType.hidden ? '_' : tile.char)
    .join();

/// 시도 이력을 🟩/⬜ 격자로. 타일 색을 못 보내는 텍스트에서는 이모지가
/// 유일한 표현이라 여기만 예외다(OVERRIDES §8).
String shareGrid(List<PuzzleAttempt> attempts) => attempts
    .map((attempt) => attempt.feedback.map((ok) => ok ? '🟩' : '⬜').join())
    .join('\n');

/// 공유 텍스트(US 10·11). 웹의 `buildShareText` 와 같은 줄 구성에 **링크 한
/// 줄만 더** 붙인다 — 앱에서 공유한 텍스트를 받은 사람이 바로 플레이할 수
/// 있어야 한다(웹은 자기 주소라 링크를 안 붙인다).
///
/// **정답은 넣지 않는다.** 아직 안 푼 사람이 받는 텍스트다.
String buildShareText({
  required String heading,
  required String puzzleLine,
  required String resultLine,
  required List<PuzzleAttempt> attempts,
}) => [
  heading,
  puzzleLine,
  resultLine,
  if (attempts.isNotEmpty) ...['', shareGrid(attempts)],
  '',
  shareUrl,
].join('\n');
