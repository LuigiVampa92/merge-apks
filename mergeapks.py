#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import platform
import shutil
import sys
from distutils.spawn import find_executable

from subprocess import call, STDOUT
try:
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')


const_dir_tmp = ".mergeapks"
const_file_target_file = "target"
const_file_result_file = "result"
const_ext_apk = ".apk"
const_apk_file_apktool_config = 'apktool.yml'
const_sign_config_properties_file = 'mergeapks.sign.properties'


def print_help():
    print("")
    print("MergeApks is a tool that merges multiple .apk files of the same application but with different resource sets (native libraries, locales, dpi) into one single universal .apk file")
    print("Usage: python mergeapks.py PATH_TO_FILE_01.apk PATH_TO_FILE_02.apk PATH_TO_FILE_03.apk ...")
    print("")


def get_param_apk_file_name(apk_number):
    return sys.argv[apk_number]


def get_param_apk_abs_path(apk_number):
    return os.path.abspath(get_param_apk_file_name(apk_number))


def check_sys_args():
    if len(sys.argv) < 3:
        return False

    for apk_number in range(1, len(sys.argv)):
        apk_file_name = get_param_apk_file_name(apk_number)
        if not apk_file_name.endswith(const_ext_apk):
            return False
        abspath_to_apk_file = os.path.abspath(apk_file_name)
        if not os.path.exists(abspath_to_apk_file):
            return False

    return True


def execute_command_os_system(command):
    rc = os.system(command)
    return rc


def execute_command_subprocess(command_tokens_list):
    rc = call(command_tokens_list, stdout=DEVNULL, stderr=STDOUT)
    return rc


def is_windows():
    return platform.system() == "Windows"


def windows_hide_file(file_path):
    execute_command_subprocess(["attrib", "+h", file_path])


def create_or_recreate_dir(dir_path):
    if os.path.exists(dir_path):
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path)
        else:
            os.remove(dir_path)
    os.mkdir(dir_path)
    if is_windows():
        windows_hide_file(dir_path)


def check_if_executable_exists_in_path(executable):
    path_to_cmd = find_executable(executable)
    return path_to_cmd is not None


def create_tmp_dir(working_dir):
    path_dir_tmp = os.path.abspath(os.path.join(working_dir, const_dir_tmp))
    create_or_recreate_dir(path_dir_tmp)
    return path_dir_tmp


def file_split_name_and_extension(file_path):
    split = os.path.splitext(file_path)
    return split[0], split[1]


def get_do_not_compress_lines(config_file_lines):
    index_start = -1
    index_end = -1
    result = list()
    start_block_literal = 'doNotCompress:'
    prefix_target_line = '- '
    opened = False
    for index, line in enumerate(config_file_lines):
        if not opened and line.startswith(start_block_literal):
            opened = True
            if index_end == -1 and index_start == -1:
                index_start = index + 1
        elif opened and line.startswith(prefix_target_line):
            result.append(line)
        elif opened and not line.startswith(prefix_target_line):
            if index_start != -1 and index_end == -1:
                index_end = index - 1
            break
    result.sort()
    return result, index_start, index_end


def parse_apktool_config(config_file_path):
    config_file_lines = list()
    with open(config_file_path, 'r') as file:
        config_file_lines = file.readlines()

    do_not_compress_lines, do_not_compress_index_start, do_not_compress_index_end = get_do_not_compress_lines(config_file_lines)

    properties = dict()
    properties['lines_all'] = config_file_lines
    properties['lines_do_not_compress'] = do_not_compress_lines
    properties['lines_do_not_compress_index_start'] = do_not_compress_index_start
    properties['lines_do_not_compress_index_end'] = do_not_compress_index_end

    return properties


def insert_new_lines_do_not_compress(config_file_path, lines_to_insert):
    file_apktool_config = parse_apktool_config(config_file_path)
    do_not_compress_lines_original = file_apktool_config['lines_do_not_compress']

    do_not_compress_lines_updated = set()
    do_not_compress_lines_updated.update(do_not_compress_lines_original)
    do_not_compress_lines_updated.update(lines_to_insert)
    do_not_compress_lines_updated = list(do_not_compress_lines_updated)
    do_not_compress_lines_updated.sort()

    config_file_lines_original = file_apktool_config['lines_all']
    config_file_lines_index_start = file_apktool_config['lines_do_not_compress_index_start']
    config_file_lines_index_end = file_apktool_config['lines_do_not_compress_index_end']
    config_file_lines_updated = list()
    for config_file_line in config_file_lines_original:
        config_file_lines_updated.append(config_file_line)
    config_file_lines_updated[config_file_lines_index_start:config_file_lines_index_end] = do_not_compress_lines_updated

    with open(config_file_path, 'w') as file:
        file.writelines(config_file_lines_updated)


def merge_dir_contents(path_src, path_dst):
    follow_symlinks_on_source_files = False
    replace_if_files_already_exist = False
    skip_file_io_errors = True

    file_names = os.listdir(path_src)
    if not os.path.isdir(path_dst):
        os.makedirs(path_dst)

    for file_name in file_names:
        file_src = os.path.join(path_src, file_name)
        file_dst = os.path.join(path_dst, file_name)
        try:
            if follow_symlinks_on_source_files and os.path.islink(file_src):
                symlink = os.readlink(file_src)
                os.symlink(symlink, file_dst)
            elif os.path.isdir(file_src):
                merge_dir_contents(file_src, file_dst)
            else:
                if not os.path.exists(file_dst) or replace_if_files_already_exist:
                    # print("COPY %s TO %s" % (file_src, file_dst))
                    shutil.copy2(file_src, file_dst)
        except Exception as e:
            if not skip_file_io_errors:
                raise e
    try:
        shutil.copystat(path_src, path_dst)
    except Exception as e:
        if not skip_file_io_errors:
            raise e


def merge_apk_contents(dir_apk_main, dir_apk_secondary):
    directories_to_merge = ['assets', 'lib', 'res', 'unknown', 'kotlin']

    for dir_to_merge in directories_to_merge:
        path_src = os.path.join(dir_apk_secondary, dir_to_merge)
        path_dst = os.path.join(dir_apk_main, dir_to_merge)
        if os.path.exists(path_src) and os.path.isdir(path_src):
            merge_dir_contents(path_src, path_dst)

    path_file_config_src = os.path.join(dir_apk_secondary, const_apk_file_apktool_config)
    path_file_config_dst = os.path.join(dir_apk_main, const_apk_file_apktool_config)
    config_src = parse_apktool_config(path_file_config_src)
    insert_new_lines_do_not_compress(path_file_config_dst, config_src['lines_do_not_compress'])


def unpack_apk(path_dir_tmp, apk_file, number_current, number_total):
    print('[*] unpacking %d of %d' % (number_current, number_total))
    os.chdir(path_dir_tmp)
    rc = execute_command_subprocess(['apktool', 'd', '-s', apk_file])
    if rc != 0:
        raise Exception("failed to unpack %s" % apk_file)
    os.remove(os.path.join(path_dir_tmp, apk_file))


def pack_apk(path_dir_tmp, main_apk_dir):
    print('[*] repack apk')
    os.chdir(path_dir_tmp)
    rc = execute_command_subprocess(['apktool', 'b', main_apk_dir])
    if rc != 0:
        raise Exception("failed to pack apk")

    built_apk_file_path = os.path.join(path_dir_tmp, main_apk_dir, 'dist', '%s%s' % (os.path.basename(main_apk_dir), const_ext_apk))
    if not os.path.exists(built_apk_file_path):
        raise Exception("result apk not found")

    build_apk_target_file = os.path.join(path_dir_tmp, '%s%s' % (const_file_target_file, const_ext_apk))
    if os.path.exists(build_apk_target_file):
        os.remove(build_apk_target_file)

    shutil.copy(built_apk_file_path, build_apk_target_file)


def zipalign_apk(path_dir_tmp):
    print('[*] zipalign apk')
    os.chdir(path_dir_tmp)

    built_apk_file_path = os.path.join(path_dir_tmp, const_file_target_file + const_ext_apk)
    if not os.path.exists(built_apk_file_path):
        raise Exception("result apk not found")

    prefix_aligned = 'aligned_'
    built_apk_file_aligned_path = os.path.join(path_dir_tmp, prefix_aligned + const_file_target_file + const_ext_apk)
    if os.path.exists(built_apk_file_aligned_path):
        os.remove(built_apk_file_aligned_path)

    rc = execute_command_subprocess(['zipalign', '-p', '-f', '4', built_apk_file_path, built_apk_file_aligned_path])
    if rc != 0:
        raise Exception("failed to zipalign apk")
    if not os.path.exists(built_apk_file_aligned_path):
        raise Exception("failed to zipalign apk")

    os.remove(built_apk_file_path)
    shutil.move(built_apk_file_aligned_path, built_apk_file_path)


def sign_apk(path_dir_tmp, sign_config):
    build_apk_target_file = os.path.join(path_dir_tmp, '%s%s' % (const_file_target_file, const_ext_apk))
    if not os.path.exists(build_apk_target_file):
        raise Exception("result apk not found")

    print('[*] resign apk')
    os.chdir(path_dir_tmp)
    rc = execute_command_subprocess(['apksigner', 'sign', '--ks', sign_config['sign.keystore.file'], '--ks-pass', 'pass:%s' % sign_config['sign.keystore.password'], '--ks-key-alias', sign_config['sign.key.alias'], '--key-pass', 'pass:%s' % sign_config['sign.key.password'], build_apk_target_file])
    if rc != 0:
        raise Exception("failed to sign apk file")


def delete_file_if_exists(path_to_file):
    if os.path.exists(path_to_file):
        os.remove(path_to_file)


def delete_signature_related_files(path_to_main_apk):
    delete_file_if_exists(os.path.join(path_to_main_apk, 'original', 'META-INF', 'BNDLTOOL.RSA'))
    delete_file_if_exists(os.path.join(path_to_main_apk, 'original', 'META-INF', 'BNDLTOOL.SF'))
    delete_file_if_exists(os.path.join(path_to_main_apk, 'original', 'META-INF', 'MANIFEST.MF'))


def update_main_manifest_file(path_main_apk):
    path_manifest = os.path.join(path_main_apk, 'AndroidManifest.xml')
    data = None

    application_propertry_splits_required_from = ' android:isSplitRequired="true" '
    application_propertry_splits_required_to = ' '
    metadata_google_play_splits_required_from = '<meta-data android:name="com.android.vending.splits.required" android:value="true"/>'
    metadata_google_play_splits_required_to = ''
    metadata_google_play_splits_list_from = '<meta-data android:name="com.android.vending.splits" android:resource="@xml/splits0"/>'
    metadata_google_play_splits_list_to = ''
    metadata_google_play_stamp_type_from = 'android:value="STAMP_TYPE_DISTRIBUTION_APK"'
    metadata_google_play_stamp_type_to = 'android:value="STAMP_TYPE_STANDALONE_APK"'

    with open(path_manifest, 'r') as file:
        data = file.read()
    data = data.replace(application_propertry_splits_required_from, application_propertry_splits_required_to)
    data = data.replace(metadata_google_play_splits_required_from, metadata_google_play_splits_required_to)
    data = data.replace(metadata_google_play_splits_list_from, metadata_google_play_splits_list_to)
    data = data.replace(metadata_google_play_stamp_type_from, metadata_google_play_stamp_type_to)
    with open(path_manifest, 'w') as file:
        file.write(data)


def load_sign_properties():
    path_sign_config_file = os.path.abspath(os.path.join(os.getcwd(), const_sign_config_properties_file))
    if not os.path.exists(path_sign_config_file):
        path_sign_config_file = os.path.abspath(os.path.join(os.path.expanduser('~'), const_sign_config_properties_file))
        if not os.path.exists(path_sign_config_file):
            return None

    sign_config_file_lines = list()
    with open(path_sign_config_file, 'r') as sign_config_file:
        sign_config_file_lines = sign_config_file.readlines()

    properties = dict()
    for line in sign_config_file_lines:
        checked_line = line.strip().replace('\r', '').replace('\n', '')
        if checked_line is None or checked_line == '' or line.startswith('#'):
            continue
        line_parts = checked_line.split('=')
        if len(line_parts) != 2:
            continue
        property_key = line_parts[0].strip()
        property_value = line_parts[1].strip()
        properties[property_key] = property_value

    if not 'sign.enabled' in properties.keys() or properties['sign.enabled'].lower() != 'true':
        return None
    if 'sign.keystore.file' not in properties.keys() or 'sign.keystore.password' not in properties.keys() or 'sign.key.alias' not in properties.keys() or 'sign.key.password' not in properties.keys():
        return None
    keystore_file = properties['sign.keystore.file']
    if keystore_file == '' or not os.path.exists(keystore_file) or os.path.isdir(keystore_file):
        return None
    if properties['sign.keystore.password'] == '' or properties['sign.key.alias'] == '' or properties['sign.key.password'] == '':
        return None

    return properties


def build_single_apk(path_to_tmp_dir, path_to_main_apk_dir, should_sign_apk, sign_config):
    pack_apk(path_to_tmp_dir, path_to_main_apk_dir)
    zipalign_apk(path_to_tmp_dir)
    if should_sign_apk:
        sign_apk(path_to_tmp_dir, sign_config)


def copy_single_apk_to_working_dir(path_to_tmp_dir, path_to_working_dir, target_name):
    file_src = os.path.join(path_to_tmp_dir, const_file_target_file + const_ext_apk)
    if not os.path.exists(file_src) or os.path.isdir(file_src):
        raise Exception("result apk file not found")

    file_dst = os.path.join(path_to_working_dir, target_name + const_ext_apk)
    if os.path.exists(file_dst):
        if os.path.isdir(file_dst):
            shutil.rmtree(file_dst)
        else:
            os.remove(file_dst)

    shutil.copy(file_src, file_dst)


def main():
    if not check_sys_args():
        print_help()
        exit(-1)

    tested_binary = "apktool"
    if not check_if_executable_exists_in_path(tested_binary):
        print("executable %s not found in $PATH, please install it before running mergeapks.py" % tested_binary)
        exit(-2)

    tested_binary = "zipalign"
    if not check_if_executable_exists_in_path(tested_binary):
        print("executable %s not found in $PATH, please install it before running mergeapks.py" % tested_binary)
        exit(-2)

    sign_properties = load_sign_properties()
    should_sign_apk = sign_properties is not None
    if should_sign_apk:
        tested_binary = "apksigner"
        if not check_if_executable_exists_in_path(tested_binary):
            print("executable %s not found in $PATH, please install it before running mergeapks.py" % tested_binary)
            exit(-2)

    print('[*] start')

    cwd = os.path.abspath(os.path.curdir)
    path_dir_tmp = create_tmp_dir(cwd)
    apk_count = len(sys.argv) - 1
    apk_numbers_range = range(1, len(sys.argv))

    files_apk = list()
    files_apk_abs_paths = list()
    files_apk_original_names = list()
    paths_target_apk_files = list()
    paths_target_apk_dirs = list()
    for apk_number in apk_numbers_range:
        apk_file_name = get_param_apk_file_name(apk_number)
        original_file_name, original_file_extension = file_split_name_and_extension(apk_file_name)
        apk_file_abs_path = get_param_apk_abs_path(apk_number)
        files_apk.append(apk_file_name)
        files_apk_abs_paths.append(apk_file_abs_path)
        files_apk_original_names.append(original_file_name)
        target_apk_file_abs_path = os.path.join(path_dir_tmp, apk_file_name)
        target_apk_dir_abs_path = os.path.join(path_dir_tmp, original_file_name)
        paths_target_apk_files.append(target_apk_file_abs_path)
        paths_target_apk_dirs.append(target_apk_dir_abs_path)
        shutil.copy(apk_file_abs_path, target_apk_file_abs_path)

    for index, target_apk in enumerate(paths_target_apk_files):
        unpack_apk(path_dir_tmp, target_apk, index + 1, apk_count)

    path_apk_main = paths_target_apk_dirs[0]
    paths_apk_secondary = paths_target_apk_dirs[1:]

    for paths_apk_secondary in paths_apk_secondary:
        merge_apk_contents(path_apk_main, paths_apk_secondary)

    delete_signature_related_files(path_apk_main)
    update_main_manifest_file(path_apk_main)

    build_single_apk(path_dir_tmp, path_apk_main, should_sign_apk, sign_properties)
    copy_single_apk_to_working_dir(path_dir_tmp, cwd, const_file_result_file)

    shutil.rmtree(path_dir_tmp)

    print('[*] complete')


if __name__ == '__main__':
    main()
