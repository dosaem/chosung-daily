import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/app_env.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

/// 계정을 연결할 수 있는 곳. 서버 `OAuthProvider` 와 같은 문자열을 쓴다.
enum AccountProvider {
  google('google'),
  apple('apple')
  ;

  const AccountProvider(this.wire);

  /// `POST /auth/token-exchange` 의 `provider` 값.
  final String wire;
}

/// 네이티브 로그인이 돌려준 것. 서버가 검증할 [idToken] 과, 애플만 주는
/// [authorizationCode](서버가 refresh token 으로 바꿔 둔다, 스펙 §A.6).
@immutable
class SocialCredential {
  const SocialCredential({
    required this.provider,
    required this.idToken,
    this.authorizationCode,
  });

  final AccountProvider provider;
  final String idToken;
  final String? authorizationCode;
}

/// 네이티브 로그인 SDK 가 사용자 취소 말고 다른 이유로 실패했다.
class SocialSignInException implements Exception {
  const SocialSignInException(this.message);

  final String message;

  @override
  String toString() => 'SocialSignInException: $message';
}

/// 구글·애플 SDK 경계. 플러그인은 플랫폼 채널을 타므로 테스트는 이 자리만
/// 가짜로 바꾸고 나머지(교환·토큰 교체·재조회)는 실제 코드를 돌린다.
///
/// 사용자가 창을 닫으면 null — 취소는 오류가 아니라서 화면에 아무 말도 하지
/// 않는다. 그 밖의 실패는 [SocialSignInException].
typedef SocialSignIn =
    Future<SocialCredential?> Function(
      AccountProvider provider,
    );

/// 실제 구현. `google_sign_in` 7.x 의 `authenticate()` 와
/// `sign_in_with_apple` 을 쓴다(스펙 §B.18).
class PlatformSocialSignIn {
  PlatformSocialSignIn({required this.serverClientId});

  /// Android 의 `serverClientId` = 웹 클라이언트 ID. 서버는 이 값을 `aud` 로
  /// 검증한다(§A.6 표). iOS 는 비워 두고 `Info.plist` 의 `GIDClientID` 를
  /// 쓴다 — 그래야 `aud` 가 iOS 클라이언트 ID 로 온다.
  final String? serverClientId;

  Future<void>? _googleReady;

  /// `initialize` 는 한 번만 부를 수 있다(플러그인 규약). 처음 누를 때 돌리고
  /// 그 Future 를 들고 있는다. 실패한 Future 를 들고 있으면 그 뒤로는 눌러도
  /// 같은 오류만 나오므로, 실패하면 버려서 다음 누름에 다시 시도한다.
  Future<void> _initializeGoogle() async {
    final ready = _googleReady ??= GoogleSignIn.instance.initialize(
      serverClientId: serverClientId,
    );
    try {
      await ready;
    } on Object {
      _googleReady = null;
      rethrow;
    }
  }

  Future<SocialCredential?> signIn(AccountProvider provider) =>
      switch (provider) {
        AccountProvider.google => _signInWithGoogle(),
        AccountProvider.apple => _signInWithApple(),
      };

  Future<SocialCredential?> _signInWithGoogle() async {
    try {
      await _initializeGoogle();
      final account = await GoogleSignIn.instance.authenticate();
      final idToken = account.authentication.idToken;
      if (idToken == null) {
        throw const SocialSignInException('구글이 id_token 을 주지 않았다');
      }
      return SocialCredential(
        provider: AccountProvider.google,
        idToken: idToken,
      );
    } on GoogleSignInException catch (error) {
      if (error.code == GoogleSignInExceptionCode.canceled) return null;
      throw SocialSignInException('${error.code}: ${error.description}');
    }
  }

  Future<SocialCredential?> _signInWithApple() async {
    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: const [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
      );
      final idToken = credential.identityToken;
      if (idToken == null) {
        throw const SocialSignInException('애플이 identityToken 을 주지 않았다');
      }
      return SocialCredential(
        provider: AccountProvider.apple,
        idToken: idToken,
        // 서버가 이걸로 refresh token 을 받아 두고 계정 삭제 때 revoke 한다.
        authorizationCode: credential.authorizationCode,
      );
    } on SignInWithAppleAuthorizationException catch (error) {
      if (error.code == AuthorizationErrorCode.canceled) return null;
      throw SocialSignInException('${error.code}: ${error.message}');
    } on SignInWithAppleException catch (error) {
      throw SocialSignInException('$error');
    }
  }
}

final socialSignInProvider = Provider<SocialSignIn>(
  (ref) => PlatformSocialSignIn(
    serverClientId: ref.watch(isIosProvider)
        ? null
        : AppEnv.googleServerClientIdOrNull,
  ).signIn,
);
