"""Sign an aligned release APK with a persistent local key. Never print secrets."""
import argparse
import hashlib
import os
from pathlib import Path
import secrets
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--java', type=Path, required=True)
    parser.add_argument('--key-dir', type=Path, required=True)
    args = parser.parse_args()
    key_dir = args.key_dir.resolve()
    key_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    key_dir.chmod(0o700)
    key = key_dir / 'minicpmv-practice-release.p12'
    password_file = key_dir / 'store-password'
    if key.exists() != password_file.exists():
        raise ValueError('Signing key/password pair incomplete; do not regenerate an existing key')
    if not key.exists():
        fd = os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(secrets.token_urlsafe(48) + '\n')
        env = dict(os.environ, PART5_KEY_PASSWORD=password_file.read_text().strip())
        subprocess.run([str(args.java/'bin/keytool'), '-genkeypair', '-noprompt',
            '-keystore', str(key), '-storetype', 'PKCS12', '-alias', 'minicpmv-practice',
            '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
            '-dname', 'CN=MiniCPM-V Practice, O=Purplebook Chapter Contributors, C=CN',
            '-storepass:env', 'PART5_KEY_PASSWORD', '-keypass:env', 'PART5_KEY_PASSWORD'],
            env=env, check=True)
        key.chmod(0o600)
    password_file.chmod(0o600)
    env = dict(os.environ, JAVA_HOME=str(args.java), PART5_KEY_PASSWORD=password_file.read_text().strip())
    build_tools = args.sdk / 'build-tools/36.0.0'
    args.out.parent.mkdir(parents=True, exist_ok=True)
    aligned = args.out.with_suffix('.aligned.apk')
    subprocess.run([str(build_tools/'zipalign'), '-f', '-p', '4', str(args.apk), str(aligned)], check=True)
    subprocess.run([str(build_tools/'apksigner'), 'sign', '--ks', str(key),
        '--ks-type', 'PKCS12', '--ks-key-alias', 'minicpmv-practice',
        '--ks-pass', 'env:PART5_KEY_PASSWORD', '--key-pass', 'env:PART5_KEY_PASSWORD',
        '--v1-signing-enabled', 'true', '--v2-signing-enabled', 'true',
        '--v3-signing-enabled', 'true', '--v4-signing-enabled', 'false',
        '--out', str(args.out), str(aligned)], env=env, check=True)
    report = subprocess.check_output([str(build_tools/'apksigner'), 'verify',
        '--verbose', '--print-certs', str(args.out)], env=env, text=True)
    args.out.with_suffix('.signature.txt').write_text(report)
    subprocess.run([str(args.java/'bin/keytool'), '-exportcert', '-rfc', '-alias',
        'minicpmv-practice', '-keystore', str(key), '-storepass:env', 'PART5_KEY_PASSWORD',
        '-file', str(args.out.parent/'signing-certificate.pem')], env=env, check=True)
    aligned.unlink()
    print(report)
    print('APK SHA256:', hashlib.sha256(args.out.read_bytes()).hexdigest())
    print('Private signing materials retained locally; keep this key for future updates.')


if __name__ == '__main__':
    main()
