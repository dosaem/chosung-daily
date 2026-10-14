import 'dart:async';

import 'package:chosung/puzzle/guess_rules.dart';
import 'package:flutter/widgets.dart';

/// 다음 KST 자정까지 남은 시간을 1초마다 다시 그린다(US 6, ADR 0001).
///
/// 모양은 쓰는 쪽이 정한다 — 퍼즐 없음 카드(S1)와 결과 시트(S2)가 같은 타이머를
/// 쓰고 글씨·아이콘만 다르다.
class PuzzleCountdown extends StatefulWidget {
  const PuzzleCountdown({
    required this.builder,
    this.now = DateTime.now,
    super.key,
  });

  /// `remaining` 은 "07:12:33" 꼴로 이미 포맷된 문자열이다.
  final Widget Function(BuildContext context, String remaining) builder;

  /// 테스트가 끼우는 가짜 시계. 앱에서는 [DateTime.now] — 기기 시간대와
  /// 무관하게 KST 자정까지를 세는 건 [timeUntilNextPuzzle] 쪽이다.
  final DateTime Function() now;

  @override
  State<PuzzleCountdown> createState() => _PuzzleCountdownState();
}

class _PuzzleCountdownState extends State<PuzzleCountdown> {
  Timer? _ticker;
  late String _remaining = _read();

  String _read() => formatCountdown(timeUntilNextPuzzle(widget.now()));

  @override
  void initState() {
    super.initState();
    _ticker = Timer.periodic(
      const Duration(seconds: 1),
      (_) => setState(() => _remaining = _read()),
    );
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.builder(context, _remaining);
}
