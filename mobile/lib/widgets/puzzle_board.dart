import 'package:chosung/api/api_models.dart';
import 'package:chosung/puzzle/board_layout.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// S1 의 보드. 문제 행(가림 타일) + 캡션 "N글자" + 시도 5행.
///
/// 시도 행은 **서버 `attempts` 이력만** 그린다 — 로컬 저장은 없다. 앱을 껐다
/// 켜도, 다른 기기에서 열어도 같은 보드가 되는 건 그래서다(US 3a).
class PuzzleBoard extends StatelessWidget {
  const PuzzleBoard({required this.puzzle, super.key});

  /// 타일 사이 간격(OVERRIDES §4). `mask` 의 `s` 자리도 이 폭을 쓴다.
  static const tileGap = 6.0;

  final TodayPuzzle puzzle;

  @override
  Widget build(BuildContext context) {
    final size = tileSize(puzzle.length);
    final emptyRows = maxAttempts - puzzle.attempts.length;

    return Column(
      children: [
        _BoardRow(cells: maskCells(puzzle.mask), size: size, isQuestion: true),
        const SizedBox(height: 8),
        Text(
          'today.length'.tr(namedArgs: {'count': '${puzzle.length}'}),
          style: Theme.of(context).textTheme.labelSmall,
        ),
        const SizedBox(height: 16),
        for (final (index, attempt) in puzzle.attempts.indexed) ...[
          _BoardRow(
            cells: attemptCells(puzzle.mask, attempt),
            size: size,
            semanticsLabel: 'today.attempt_row'.tr(
              namedArgs: {'index': '${index + 1}'},
            ),
          ),
          const SizedBox(height: tileGap),
        ],
        for (var row = 0; row < emptyRows; row++) ...[
          _BoardRow(cells: emptyRowCells(puzzle.mask), size: size),
          const SizedBox(height: tileGap),
        ],
      ],
    );
  }
}

/// 한 행. 9글자 이상은 가로 스크롤 없이 줄바꿈한다(OVERRIDES §4).
class _BoardRow extends StatelessWidget {
  const _BoardRow({
    required this.cells,
    required this.size,
    this.isQuestion = false,
    this.semanticsLabel,
  });

  final List<BoardCell> cells;
  final double size;
  final bool isQuestion;
  final String? semanticsLabel;

  @override
  Widget build(BuildContext context) {
    final row = Wrap(
      alignment: WrapAlignment.center,
      spacing: PuzzleBoard.tileGap,
      runSpacing: PuzzleBoard.tileGap,
      children: [
        for (final cell in cells)
          cell.kind.isGap
              ? const BoardGap()
              : BoardTile(cell: cell, size: size, isQuestion: isQuestion),
      ],
    );

    final label = semanticsLabel;
    if (label == null) return row;
    return Semantics(container: true, label: label, child: row);
  }
}

/// 타일 사이 간격 — `mask` 의 `s`. 타일이 아니라서 글자도 면도 없다.
class BoardGap extends StatelessWidget {
  const BoardGap({super.key});

  @override
  Widget build(BuildContext context) =>
      const SizedBox(width: PuzzleBoard.tileGap);
}

/// 타일 한 칸. 색은 OVERRIDES §2 의 게임 피드백 토큰만 쓰고 brand 와 섞지 않는다.
/// 맞은 칸엔 체크 아이콘, 틀린 칸엔 취소선을 같이 둔다 — 색만으로 구분하지
/// 않아야 색각 이상이 있어도 읽을 수 있다(US 3).
class BoardTile extends StatelessWidget {
  const BoardTile({
    required this.cell,
    required this.size,
    this.isQuestion = false,
    super.key,
  });

  final BoardCell cell;
  final double size;
  final bool isQuestion;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final background = switch (cell.kind) {
      BoardCellKind.correct => colors.tileCorrect,
      BoardCellKind.wrong => colors.tileWrong,
      // 문제 행의 보이는 타일도 빈 타일과 같은 면을 쓴다(목업 e1_home).
      BoardCellKind.letter || BoardCellKind.empty => colors.tileEmpty,
      BoardCellKind.gap => colors.tileEmpty,
    };
    final foreground = cell.kind == BoardCellKind.correct
        ? colors.tileTextOnCorrect
        : colors.foreground;

    return Semantics(
      label: _semanticsLabel(),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: background,
          // 타일엔 테두리 없음(OVERRIDES §2 `tile-empty`).
          borderRadius: BorderRadius.circular(8),
        ),
        child: Stack(
          children: [
            Center(
              child: Text(
                cell.char,
                style: TextStyle(
                  // 문제 타일은 28pt bold(OVERRIDES §3), 시도 행은 한 단계 작게.
                  fontSize: isQuestion ? 28 : 20,
                  fontWeight: FontWeight.w700,
                  color: foreground,
                  decoration: cell.kind == BoardCellKind.wrong
                      ? TextDecoration.lineThrough
                      : null,
                  decorationColor: foreground,
                  decorationThickness: 2,
                ),
              ),
            ),
            if (cell.kind == BoardCellKind.correct)
              Positioned(
                top: 2,
                right: 2,
                child: Icon(LucideIcons.check, size: 12, color: foreground),
              ),
          ],
        ),
      ),
    );
  }

  /// 스크린 리더는 타일 색을 못 읽는다 — 글자와 판정을 말로 붙여준다.
  String _semanticsLabel() => switch (cell.kind) {
    BoardCellKind.correct => '${cell.char} ${'today.tile_correct'.tr()}',
    BoardCellKind.wrong => '${cell.char} ${'today.tile_wrong'.tr()}',
    BoardCellKind.letter => cell.char,
    BoardCellKind.empty || BoardCellKind.gap => 'today.tile_blank'.tr(),
  };
}
