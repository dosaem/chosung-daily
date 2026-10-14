import 'package:chosung/api/api_models.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';

/// 입력 + 글자수 카운터 + `primary-button` 제출.
///
/// 입력 중인 텍스트는 이 위젯이 아니라 **화면이 들고 있는
/// [TextEditingController]** 에 있다 — 폭이 바뀌면(회전·Split View) 입력창이
/// 다른 열로 옮겨 가면서 위젯이 다시 만들어질 수 있고, 그때 치던 답이
/// 사라지면 안 된다(SCREENS "태블릿 레이아웃").
class GuessInput extends StatelessWidget {
  const GuessInput({
    required this.puzzle,
    required this.controller,
    required this.onSubmit,
    this.enabled = true,
    super.key,
  });

  final TodayPuzzle puzzle;
  final TextEditingController controller;
  final VoidCallback onSubmit;

  /// 오프라인·제출 중에는 잠근다(SCREENS S1 상태).
  final bool enabled;

  @override
  Widget build(BuildContext context) =>
      ValueListenableBuilder<TextEditingValue>(
        valueListenable: controller,
        builder: (context, value, _) {
          // 카운터도 제출 가능 판정도 "구분자를 뺀 글자 수" 로 센다 — 서버
          // `length` 와 같은 기준이어야 en 의 "red fox" 가 4글자로 안 보인다.
          final typed = normalizeGuess(puzzle.language, value.text).length;
          final complete = typed == puzzle.length;

          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: controller,
                enabled: enabled,
                textInputAction: TextInputAction.done,
                onSubmitted: enabled && complete ? (_) => onSubmit() : null,
                // en 은 구분자까지 칠 수 있으니 그만큼 여유를 준다. 기본
                // enforcement 가 "조합 중에는 자르지 않음" 이라 한글 IME 가
                // 끊기지 않는다.
                maxLength: puzzle.length + puzzle.separatorCount,
                decoration: InputDecoration(
                  hintText: 'today.input_hint'.tr(),
                  // 우리 카운터를 쓰므로 Material 기본 카운터는 끈다.
                  counterText: '',
                  // 카운터는 입력 칸 안 오른쪽에 붙인다. `Align` 으로 감싸면
                  // 남은 폭을 전부 먹어서 정작 치는 글자가 0폭이 된다.
                  suffixIcon: Padding(
                    padding: const EdgeInsets.only(left: 8, right: 16),
                    // widthFactor 1 = 가로는 글자 폭만, 세로는 입력 칸 가운데.
                    child: Center(
                      widthFactor: 1,
                      child: Text(
                        'today.counter'.tr(
                          namedArgs: {
                            'typed': '$typed',
                            'total': '${puzzle.length}',
                          },
                        ),
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ),
                  ),
                  suffixIconConstraints: const BoxConstraints(minHeight: 48),
                ),
              ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: enabled && complete ? onSubmit : null,
                child: Text('today.submit'.tr()),
              ),
            ],
          );
        },
      );
}

/// "남은 기회 3/5". expanded 태블릿에서는 입력 아래가 아니라 오른쪽 열로
/// 옮겨 가므로(SCREENS T1) 입력과 한 위젯으로 묶지 않는다.
class AttemptsLeftLabel extends StatelessWidget {
  const AttemptsLeftLabel({required this.attemptsLeft, super.key});

  final int attemptsLeft;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Text(
      'today.attempts_left'.tr(
        namedArgs: {'left': '$attemptsLeft', 'max': '$maxAttempts'},
      ),
      style: Theme.of(
        context,
      ).textTheme.labelSmall?.copyWith(color: colors.mutedForeground),
    );
  }
}
