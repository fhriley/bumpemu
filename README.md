# bumpemu
This is a bump controller emulator for CellPro PowerLab 6 and 8 chargers.
It allows you to use the CCS mobile app to control your charger over
bluetooth low energy (BLE).

To interface to the PowerLab with BLE, you need two pieces of hardware:

[FUIM3 USB Adapter](http://www.usastore.revolectrix.com/Products_2/Cellpro-PowerLab-8-EC5-version_2/FUIM3_136)

[Raspberry Pi Zero W](https://smile.amazon.com/gp/product/B072N3X39J)

If you've ever hooked up your PowerLab to your PC and monitored charging,
you already have the FUIM3.

### Pi Zero W Setup

This controller emulator will run on the Pi Zero W. Follow the
[instructions](https://www.canakit.com/quick-start/pi) for installing the
Pi with the latest version of [Raspbian](http://raspbian.org).

Once you have the Pi up and running, make sure everything is up to date:

    sudo apt-get update
    sudo apt-get upgrade

Then install the required libraries:

    sudo apt-get install -y libusb-dev libdbus-1-dev libglib2.0-dev libudev-dev libical-dev libreadline-dev libgirepository1.0-dev libcairo2-dev

The Pi will come with `bluez` already installed, but it will probably be an
older version. Version `5.45` has proven to work well so you will need to
install it. Download it from [here](http://www.kernel.org/pub/linux/bluetooth/bluez-5.45.tar.xz).
Then follow [these instructions](https://learn.adafruit.com/install-bluez-on-the-raspberry-pi/installation)
to install it. Make sure to do the step where you enable the experimental
features.

Finally, `bumpemu` can be installed using `pip`:
    
    sudo pip3 install bumpemu

Then you can run bumpemu as follows:

    /usr/local/bin/bumpemu-controller
    
You can view various configuration options with `-h`:

    /usr/local/bin/bumpemu-controller -h
    
A systemd service is in the repo if you wish to have bumpemu run at boot.

### Presets configuration

The `BumpCCS2` app has 7 predefined charger profiles: 
* Accurate
* Analyze
* Discharge
* Fastest
* Monitor
* Normal
* Storage

Bumpemu will map the app's predefined profiles to existing presets in your charger. To do this, create the file `/etc/bumpemu/presets.yml` on your pi. Set the number of the charger preset you want each app charger profile to map to. [An example presets file is in the repo](bumpemu/config/presets.yml).

To verify you have set the profiles the way you want them, make sure no other instances of `bumpemu-controller` are running, and then run the following:

    /usr/local/bin/bumpemu-controller --show-presets

### Battery configuration

When running the `BumpCCS` app with a real bump controller, you would bump a battery to load the battery configuration to the app. To emulate that, `bumpemu` loads a battery configuration when it starts up. The battery configuration should go in `/etc/bumpemu/battery.yml`. [An example battery configuration file is in the repo](bumpemu/config/battery_example.yml).
