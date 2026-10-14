"""Build the v23 practice release and sign with the caller's persistent local key."""
import argparse
from pathlib import Path
import os
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream', type=Path, default=Path('vendor/MiniCPM-V-Apps'))
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--java', type=Path, required=True)
    parser.add_argument('--key-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('dist/apk-release/MiniCPM-V-demo-Android-v2.5.apk'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    upstream = args.upstream.resolve()
    subprocess.run([os.sys.executable, str(root/'examples/integrate_inspection_android.py'),
                    '--upstream', str(upstream)], check=True)
    app = upstream/'MiniCPM-V-demo-Android/app'
    gradle = app/'build.gradle.kts'
    text = gradle.read_text()
    if 'applicationIdSuffix = ".practice"' not in text:
        assert text.count('        release {\n') == 1
        text = text.replace('        release {\n', '        release {\n            applicationIdSuffix = ".practice"\n')
    text = text.replace('if (signingCfg.storeFile?.exists() == true) {',
        'if (providers.gradleProperty("PART5_UNSIGNED").orNull != "true" && signingCfg.storeFile?.exists() == true) {')
    gradle.write_text(text)
    resources = root/'android/release'
    for source in resources.rglob('*'):
        if source.is_file():
            target=app/'src/release'/source.relative_to(resources)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
    environment=dict(os.environ,JAVA_HOME=str(args.java.resolve()),ANDROID_HOME=str(args.sdk.resolve()))
    subprocess.run(['./gradlew',':app:assembleRelease','-PPART5_UNSIGNED=true','--console=plain'],
                   cwd=upstream/'MiniCPM-V-demo-Android',env=environment,check=True)
    subprocess.run([os.sys.executable,str(root/'examples/sign_part5_apk.py'),'--apk',
        str(app/'build/outputs/apk/release/app-release-unsigned.apk'),'--out',str(args.out.resolve()),
        '--sdk',str(args.sdk.resolve()),'--java',str(args.java.resolve()),
        '--key-dir',str(args.key_dir.resolve())],check=True)


if __name__=='__main__':main()
