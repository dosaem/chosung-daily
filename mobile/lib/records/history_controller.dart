import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S4 7일 그리드의 데이터. 재시도는 `ref.invalidate(historyProvider)` 다 —
/// 여기엔 상태 전이가 없어서(읽기 한 번) Notifier 를 둘 이유가 없다.
final historyProvider = FutureProvider<List<HistoryDay>>(
  (ref) => ref.read(apiClientProvider).fetchMyHistory(),
);
