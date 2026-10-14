/// Riverpod 3 은 실패한 provider 를 기본 10회까지 백오프로 다시 빌드한다.
///
/// 이 앱은 네트워크 오류를 인라인 카드 + 재시도 버튼으로 보여주기로 했으므로
/// (OVERRIDES §7 "토스트로 숨기지 않는다") 자동 재시도를 끈다. 켜두면 사용자는
/// 최대 수십 초 동안 스켈레톤만 보게 되고, 재시도는 눌러야 일어나야 한다.
Duration? noAutoRetry(int retryCount, Object error) => null;
