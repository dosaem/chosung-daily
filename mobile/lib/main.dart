import 'package:chosung/app.dart';
import 'package:chosung/config/app_env.dart';
import 'package:chosung/config/firebase_bootstrap.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/config/sentry_bootstrap.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeFirebase();

  await runWithSentry(
    dsn: AppEnv.sentryDsn,
    runApp: () => runApp(
      const ProviderScope(
        retry: noAutoRetry,
        child: AppLocalizationScope(child: ChosungApp()),
      ),
    ),
  );
}
