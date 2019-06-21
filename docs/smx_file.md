i.MX MakeImage Tool - SMX File
==============================

The SMX file is a standard text file which collect all parts of i.MX boot image. Thanks to YAML syntax is human-readable 
and easy modifiable. Comments in SMX file start with the hash character `#` and extend to the end of the physical line. A 
comment may appear at the start of a line or following whitespace characters. The content of SMX file is split into four 
sections: `HEAD`, `VARS`, `DATA` and `BODY`.

#### HEAD Section:

This section contains the base information's about target device.

* **NAME** - The name of target device or evaluation board (optional)
* **DESC** - The description of target device or evaluation board (optional)


Example of head section:

```
HEAD:
    NAME: MCIMX7SABRE
    DESC: Development Board Sabre SD for IMX7D
```


#### VARS Section:

Collects all variables used in `DATA` and `BODY` section. 

The syntax for defining a variable is following:

```
VARS:
    #   <name>: <value>
    DIR_NAME: imx7d_sbd
```

The syntax for using a variable in `DATA` or `BODY` section is following:

```
DATA:
    ddr_init.dcd:
        DESC: Device Configuration Data
        FILE: "{{ DIR_NAME }}/dcd_micron_1gb.txt"
```

#### DATA Section:

Collects all data segments which can be loaded into the target via scripts in `BODY` section. Individual data segments 
can contain a different type of data what is specified by extension in its name `<segment_name>.<data_type>`. Supported are following data types:

* **DCD** - Device configuration data
* **FDT** - Flattened device tree data (*.dtb, *.dts)
* **IMX2** - Vybrid, i.MX6 and i.MX7 boot image (*.imx)
* **IMX2B** - i.MX8M boot image (*.imx)
* **IMX3** - i.MX8DM, i.MX8QM and i.MX8QXP boot image (*.imx)
* **UBI** - U-Boot main image (*.img, *.bin)
* **UBX** - Old format of U-Boot executable image (script, firmware, ...)
* **UBT** - New format of U-Boot executable image based on FDT (script, firmware, ...)
* **UEV** - U-Boot environment variables image 
* **RAW** - Binary raw image (*.*)

Attributes common for all data segments are:

* **DESC** - The description of data segments (optional)
* **DATA or FILE** - The data itself or path to image (required)

##### Device configuration data segment (DCD)

This data segments contains a data which generally initialize the SoC periphery for DDR memory. More details about DCD 
are in reference manual of selected IMX device. The data itself can be specified as binary file or text string/file. The 
text format of DCD data is described here: [imxim](https://github.com/molejar/pyIMX/blob/master/doc/imxim.md#dcd-file)

Example of *DCD* data segments in binary and text format:

```
DATA:
    ddr_init_bin.dcd:
        DESC: Device Configuration Data
        FILE: imx7d/dcd.bin
            
    ddr_init_txt.dcd:
        DESC: Device Configuration Data
        DATA: |
            # DDR init
            WriteValue    4 0x30340004 0x4F400005
            WriteValue    4 0x30391000 0x00000002
            WriteValue    4 0x307A0000 0x01040001
            ...
```

##### Flattened device tree data segment (FDT)

This data segments cover device tree data in readable text format or binary blob format.   

Optional attributes:

* **MODE** - Data insert mode: disabled or merge (optional)
* **DATA** - This attribute can be used for customizing loaded *.dtb or *.dts via `FILE` attribute. Its content will be
merged with loaded data if `MODE: merge`

Example of *FDT* data segments:

```
    kernel_dtb.fdt:
        DESC: Device Tree Blob
        FILE: imx7d/imx7d-sdb.dtb
        # insert mode (disabled or merge)
        MODE: merge
        # modifications in loaded file
        DATA: |
            // Add support for M4 core
            / {
                memory {
                    linux,usable-memory = <0x80000000 0x1FF00000 0xA0000000 0x1FF00000>;
                };
```

##### Vybrid, i.MX6 and i.MX7 boot image data segment (IMX2)

This data segments represent a complete boot image for Vybrid, i.MX6 and i.MX7 device which at least consist of DCD
and UBI images. The data for it can be specified as path to a standalone file or can be created from others segments.

Optional attributes for IMX2 data segments based on standalone file (U-Boot IMX image):

* **MODE** - Environment variables insert mode: disabled, merge or replace (optional)
* **MARK** - Environment variables start mark in u-boot image (default: 'bootdelay=')
* **EVAL** - Environment variables itself

Example of *IMX2* data segments:

```
DATA:
    uboot_file.imx2:
        DESC: U-Boot Image
        FILE: imx7d/u-boot.imx
        # Environment variables insert mode (disabled, merge or replace)
        MODE: merge
        # Environment variables start mark in u-boot image
        MARK: bootcmd=
        # Environment variables
        EVAL: |
            bootdelay = 0
            bootcmd = echo Running bootscript ...; source 0x83100000
            
    uboot_image.imx2:
        NAME: U-Boot Image
        DATA:
            STADDR: 0x877FF000
            OFFSET: 0x400
            DCDSEG: ddr_init_txt.dcd
            APPSEG: uboot_main_image.ubi
```

##### U-Boot main image data segment (UBI)

This data segments cover a raw U-Boot image without IVT, DCD and other parts which are included in i.MX image. Therefore
it can not be loaded into target directly but can be used for creation of IMX2, IMX2B and IMX3 data segments.

Optional attributes:

* **MODE** - Environment variables insert mode: disabled, merge or replace (optional)
* **MARK** - Environment variables start mark in u-boot image (default: 'bootdelay=')
* **EVAL** - Environment variables itself

Example of *UBI* data segments:

```
DATA:
    uboot_main_image.ubi:
        DESC: U-Boot Raw Image
        FILE: imx7d/u-boot.img
        # Environment variables insert mode (disabled, merge or replace)
        MODE: merge
        # Environment variables start mark in u-boot image
        MARK: bootcmd=
        # Environment variables
        EVAL: |
            bootdelay = 0
            bootcmd = echo Running bootscript ...; source 0x83100000
```

##### U-Boot executable image data segment (UBX)

This data segments cover a data which can be executed from U-Boot environment. Format of input data depends on image type
which is defined by `HEAD` attribute.

All HEAD attributes:

* **nane**     - Image name in 32 chars (default: "-")
* **eaddr**    - Entry address value (default: 0x00000000)
* **laddr**    - Load address value (default: 0x00000000)
* **image**    - Image type: "standalone", "firmware", "script", "multi" (default: "firmware")
* **arch**     - Architecture type: "alpha", "arm", "x86", ... (default: "arm")
* **os**       - OS type: "openbsd", "netbsd", "freebsd", "bsd4", "linux", ... (default: "linux")
* **compress** - Compression type: "none", "gzip", "bzip2", "lzma", "lzo", "lz4" (default: "none")



Example of *UBX* data segments:

```
DATA:      
    uboot_firmware.ubx:
        DESC: U-Boot FW Image
        FILE: imx7d/u-boot.bin
                 
    uboot_script.ubx:
        DESC: NetBoot Script
        HEAD:
            image: script
        DATA: |
            echo '>> Network Boot ...'
            setenv autoload 'no'
            dhcp
            ...
```

##### New format of U-Boot executable image data segment (UBT)

...

Example of *UBT* data segments:

```
DATA:
    uboot_executable.ubt:
        DESC: U-Boot FIT Image
        FILE: imx7d/u-boot.its
```

##### U-Boot environment variables image (UEV)

...

Example of *UEV* data segments:

```
DATA:
    uboot_environment.uev:
        DESC: U-Boot environment variables
        FILE: imx7d/u-boot_env.txt

DATA:
    uboot_environment.uev:
        DESC: U-Boot environment variables
        DATA: |
            ... 
```

##### Binary raw image data segment (RAW)

This data segments is covering all images which are loaded into target as binary blob, like: kernel, initramfs, ...

Example of *RAW* data segments:

```
DATA:
    kernel_image.raw:
        DESC: Kernel Image
        FILE: imx7d/zImage
```

#### BODY Section:


Here is an example of complete i.MX SmartBoot description file: [example.smx](example.smx)
