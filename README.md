# MergeApks

A simple standalone Python script with no extra library dependencies that merges multiple `.apk` files (like in `aab` format, or splitted by native libraries arch (`arm64-v8a`, `armeabi-v7a`, `x86_64`, `x86`), dpi resources (`xxxhdpi`, `xxhdpi`, `xhdpi`, `hdpi`, etc.), string localizations (`en`, `de`, etc.), etc. by the app store) into a single universal old-school "fat" `.apk` file.

## Preparation

First, you have to get all the split apk files you want to merge. There are multiple ways to do this.

### Dump apk files of an installed application from a device by using the `adb` tool

If you want to merge an apk from your device installed from the Google Play Store, you must first dump those apk files from your device to our computer using the `adb` tool.

Let's see an example of the Telegram app.

First, install it from Google Play. Second, we have to know its package name. The `pm` commandline tool can give us all the paths to all apk files. We know that the app's package name should contain a `telegram` string. Let's find it via the `pm` tool among all installed third-party applications on the device (`pm list packages` to get all the installed application packages, and `-3` flag to filter only user-installed packages):

```
$ adb shell pm list packages -3 | grep telegram

package:org.telegram.messenger
```

Now, we know its package name: `org.telegram.messenger`. Let's get the apk file paths:

```
$ adb shell pm path org.telegram.messenger

package:/data/app/~~cMh9jYycQY1WXQGmCCN5bw==/org.telegram.messenger-9E3jXBJfFDorL8hQKF-xRg==/base.apk
package:/data/app/~~cMh9jYycQY1WXQGmCCN5bw==/org.telegram.messenger-9E3jXBJfFDorL8hQKF-xRg==/split_config.arm64_v8a.apk
package:/data/app/~~cMh9jYycQY1WXQGmCCN5bw==/org.telegram.messenger-9E3jXBJfFDorL8hQKF-xRg==/split_config.en.apk
package:/data/app/~~cMh9jYycQY1WXQGmCCN5bw==/org.telegram.messenger-9E3jXBJfFDorL8hQKF-xRg==/split_config.xxhdpi.apk
``` 

Now all we have to do is dump these files via the `adb pull` command:
```
$ adb pull /data/app/~~cMh9jYycQY1WXQGmCCN5bw==/org.telegram.messenger-9E3jXBJfFDorL8hQKF-xRg==/base.apk
$ adb pull /data/app/~~cMh9jYycQY1WXQGmCCN5bw==/org.telegram.messenger-9E3jXBJfFDorL8hQKF-xRg==/split_config.arm64_v8a.apk
$ adb pull /data/app/~~cMh9jYycQY1WXQGmCCN5bw==/org.telegram.messenger-9E3jXBJfFDorL8hQKF-xRg==/split_config.en.apk
$ adb pull /data/app/~~cMh9jYycQY1WXQGmCCN5bw==/org.telegram.messenger-9E3jXBJfFDorL8hQKF-xRg==/split_config.xxhdpi.apk
```

Alternatively, this can all be done in a single convenient one-liner:
```
adb shell pm path org.telegram.messenger | sed 's/package://g' | xargs -L 1 adb pull
```

If you use `zsh` on MacOS or Linux distro, you can use this function (add it to your `.zshrc` file): 
```
function pullapks() {
    adb shell pm path $1 | sed 's/package://g' | xargs -L 1 adb pull
}
```

And then just call it like this:
```
pullapks org.telegram.messenger
```

### Get apk files of an application from an external third-party service like `apkcombo`

There are a number of services that allow you to download applications from Google Play for different device profiles via a convenient web interface.

For example, you want to have an apk that will have native libraries for all possible architectures.
You simply download multiple different versions of it from `apkcombo` settings for a different architecture type (`arm64-v8a`, `armeabi-v7a`, `x86_64`, `x86`) for each download.
Then you can merge them all with the script and get a universal apk this way.

## Usage

The usage of the script is very simple.

First, clone the repo and make sure the script has execution permission:
```
git clone https://github.com/LuigiVampa92/merge-apks
cd merge-apks
chmod +x mergeapks.py
```

Get your apk files ready, put them near the script, and execute the script: 
```
python mergeapks.py base.apk split_config.arm64-v8a.apk split_config.xxhdpi.apk split_config.en.apk
```

Note that you must set the path to the `base` apk as the first argument and paths to other config apks after it as subsequent arguments.

You can put the symlink to this script into the path. Like this (the absolute path to the script depends on your OS and home directory settings):
```
ln -s /home/username/github/merge-apks/mergeapks.py /usr/local/bin/mergeapks
``` 
After that, the script can be executed from any directory, like this:
```
mergeapks base.apk split_config.arm64-v8a.apk split_config.xxhdpi.apk split_config.en.apk
```
The result apk file `result.apk` will be placed into your current working directory, from which you have executed the script.

## Requirements

You do not need any Python dependencies to run the script; however, you **MUST** have some tools installed in your OS, and paths to their executable **MUST** be set to the `$PATH` environment variable. The script relies on that.

These tools are [apktool](https://github.com/iBotPeaches/Apktool), [zipalign](https://developer.android.com/tools/zipalign) and [apksigner](https://developer.android.com/tools/apksigner).

`apktool` can be installed via your OS package manager: `apt`, `brew`, whatever, or pulled directly from GitHub. `zipalign` and `apksigner` are part of the Android SDK build-tools distribution and must be installed via `sdkmanager` in Android Studio or via CLI.

Do not forget to make symlinks of these tools to the system's `$PATH` environment variable, OR add the entire build-tools directory to it.

## Signing the result apk

Since repackaging the splitted app bundle into the universal apk requires changing the original app's manifest file, the original signature will be broken, and the app must be resigned before you can install it on a real device.

The easiest way to do it is to create an `mergeapks.sign.properties` file with the values of your keystore file (see `mergeapks.sign.properties.example` for an example).
This file must be placed in the same directory with `mergeapks.py` script, OR you can put it in your user home directory (`~`).
This way, repacked apk files will be signed automatically. 

If you don't want to create a dedicated keystore to sign the result apk files, you can use your default Android SDK debug keystore. In this case, the contents of the `mergeapks.sign.properties` file should look like this:
```
sign.enabled=true
sign.keystore.file=/home/username/.android/debug.keystore 
sign.keystore.password=android
sign.key.alias=androiddebugkey
sign.key.password=android
```
The `sign.keystore.file` value in the example above is for Linux. Set the absolute path according to your OS and system user name.

By default, the resigning of the result apk files is disabled.
If you do not want to sign it automatically, you don't have to do it. You can just sign the apk file manually after the conversion is completed.
