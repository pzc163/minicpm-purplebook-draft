"""Install chapter inspection sources into the pinned upstream Android project."""
import argparse
from pathlib import Path
import shutil
import re
import subprocess
import xml.etree.ElementTree as ET

PINNED = 'd1aac05eecaac64b7fc35f1cc93a06b726ce10e3'
ANDROID = '{http://schemas.android.com/apk/res/android}'


def integrate(upstream: Path):
    revision = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != PINNED:
        raise ValueError(f'Expected pinned Apps commit {PINNED}, got {revision}')
    root = Path(__file__).resolve().parent.parent
    for filename in ['0001-minicpmv-system-prompt.patch', '0002-inspection-module-entry.patch']:
        patch = root / 'android/patches' / filename
        reverse = subprocess.run(['git', '-C', str(upstream), 'apply', '--reverse', '--check', str(patch)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if reverse.returncode != 0:
            subprocess.run(['git', '-C', str(upstream), 'apply', '--check', str(patch)], check=True)
            subprocess.run(['git', '-C', str(upstream), 'apply', str(patch)], check=True)
    app = upstream / 'MiniCPM-V-demo-Android/app'
    sources = app / 'src/main/java/com/example/minicpm_v_demo'
    for name in ['InspectionActivity.kt', 'InspectionRunner.kt', 'InspectionRecordStore.kt',
                 'InspectionModelContext.kt', 'InspectionImageProcessor.kt', 'InspectionEntry.kt']:
        shutil.copyfile(root / 'android' / name, sources / name)
    tests = app / 'src/androidTest/java/com/example/minicpm_v_demo'
    tests.mkdir(parents=True, exist_ok=True)
    for name in ['InspectionContractInstrumentedTest.kt', 'InspectionVisionInstrumentedTest.kt',
                 'InspectionBenchmarkInstrumentedTest.kt', 'InspectionImageInstrumentedTest.kt']:
        shutil.copyfile(root / 'android' / name, tests / name)
    shutil.copyfile(root / 'android/InspectionTestManifest.xml', app / 'src/androidTest/AndroidManifest.xml')
    build = app / 'build.gradle.kts'
    code = build.read_text()
    version = re.search(r'versionCode\s*=\s*(\d+)', code)
    if version is None:
        raise ValueError('Missing versionCode')
    if int(version.group(1)) < 23:
        code = code[:version.start(1)] + '23' + code[version.end(1):]
    if 'applicationIdSuffix = ".inspection"' not in code:
        needle = '    buildTypes {\n        release {'
        if code.count(needle) != 1:
            raise ValueError('Unexpected buildTypes; refusing ambiguous patch')
        code = code.replace(needle, '    buildTypes {\n        debug {\n            applicationIdSuffix = ".inspection"\n            versionNameSuffix = "-inspection-validation"\n        }\n        release {')
    build.write_text(code)
    ET.register_namespace('android', ANDROID[1:-1])
    manifest = app / 'src/main/AndroidManifest.xml'
    tree = ET.parse(manifest)
    application = tree.getroot().find('application')
    if application is None:
        raise ValueError('Missing Android application')
    activities = {x.get(ANDROID + 'name'): x for x in application.findall('activity')}
    main = activities.get('.MainActivity')
    if main is None:
        raise ValueError('Missing upstream MainActivity')
    # One launcher opens the complete upstream application; inspection is an internal module.
    for item in activities.values():
        for intent in list(item.findall('intent-filter')):
            if any(x.get(ANDROID + 'name') == 'android.intent.category.LAUNCHER'
                   for x in intent.findall('category')):
                item.remove(intent)
    main.set(ANDROID + 'exported', 'true')
    intent = ET.SubElement(main, 'intent-filter')
    ET.SubElement(intent, 'action', {ANDROID + 'name': 'android.intent.action.MAIN'})
    ET.SubElement(intent, 'category', {ANDROID + 'name': 'android.intent.category.LAUNCHER'})
    activity = activities.get('.InspectionActivity')
    if activity is None:
        activity = ET.SubElement(application, 'activity', {ANDROID + 'name': '.InspectionActivity'})
    activity.attrib.update({ANDROID + 'exported': 'false', ANDROID + 'label': '巡检助手',
                           ANDROID + 'windowSoftInputMode': 'adjustResize',
                           ANDROID + 'configChanges': 'orientation|screenSize',
                           ANDROID + 'parentActivityName': '.MainActivity',
                           ANDROID + 'process': ':inspection'})
    activity.attrib.pop(ANDROID + 'launchMode', None)
    if not any(x.get(ANDROID + 'authorities') == '${applicationId}.inspection.files' for x in application.findall('provider')):
        provider = ET.SubElement(application, 'provider', {
            ANDROID + 'name': 'androidx.core.content.FileProvider',
            ANDROID + 'authorities': '${applicationId}.inspection.files',
            ANDROID + 'exported': 'false', ANDROID + 'grantUriPermissions': 'true'})
        ET.SubElement(provider, 'meta-data', {
            ANDROID + 'name': 'android.support.FILE_PROVIDER_PATHS',
            ANDROID + 'resource': '@xml/inspection_file_paths'})
    ET.indent(tree, space='    ')
    tree.write(manifest, encoding='utf-8', xml_declaration=True)
    main_xml = app / 'src/main/res/xml'
    (main_xml / 'inspection_file_paths.xml').write_text('''<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <files-path name="inspection" path="inspection/" />
</paths>
''')
    debug = app / 'src/debug'
    (debug / 'res/xml').mkdir(parents=True, exist_ok=True)
    (debug / 'AndroidManifest.xml').write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android" xmlns:tools="http://schemas.android.com/tools">
    <application android:label="MiniCPM-V 实践版"
        android:networkSecurityConfig="@xml/inspection_debug_network"
        tools:replace="android:label,android:networkSecurityConfig" />
</manifest>
''')
    # Drop the former standalone inspection launcher icon; use the upstream app icon.
    (debug / 'res/mipmap-anydpi/ic_inspection.xml').unlink(missing_ok=True)
    (debug / 'res/xml/inspection_debug_network.xml').write_text('''<network-security-config>
    <base-config cleartextTrafficPermitted="false" />
    <domain-config cleartextTrafficPermitted="true">
        <domain>127.0.0.1</domain>
        <domain>localhost</domain>
    </domain-config>
</network-security-config>
''')
    print(f'Integrated inspection sources in {app}; upstream {revision}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream', type=Path, default=Path('vendor/MiniCPM-V-Apps'))
    integrate(parser.parse_args().upstream.resolve())
