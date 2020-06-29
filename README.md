# TP-Link EAP245v3 OpenWrt factory images

## Signed safeloader format
The firmware images provided by TP-Link consist of a safeloader
image, concatened with a 1024 bit MD5 RSA digest.
Although the image format is relativeley well understood, it is
impossible to generate valid firmware files since they cannot be
provided with a valid signature without the private key.

## 3rd firmware format
This appears to be an older OpenWrt image format, or a derivative thereof.

The sources included in this repository allow converting an OpenWrt
sysupgrade file, built for the TP-Link EAP245v3, into a factory image
that is accepted by the device's web-interface.

Firmware versions that should accept this image type:
* v2.2 (190530)
* v2.3 (190731)
* v2.4 (191029)

The image format was derived from the libnvrammanager.so of the EAP245v3
firmware v2.4. Image uploads were tested on v2.3. You can check if this
format might work on your device by extracting the squashfs (`binwalk -e`).
Check `/lib/libnvrammanager.so` for strings with "3rd" or "openwrt".
So far, only the EAP245v3 appears to have this libnvrammanager.

```
$ strings libnvrammanager.so | grep -e "3rd" -e "openwrt"
nm_api_get3rdFwChkStatus
nm_fwup_get3rdFwChkStatus
nm_api_check3rdUpgradeFile
nm_fwup_check3rdUpgradeFile
nm_api_upgrade3rdFwupFile
nm_fwup_upgrade3rdFwupFile
l_nmFwup3rdPtnEntry
nm_api_get3rdFwChkStatus
nm_api_check3rdUpgradeFile
nm_api_upgrade3rdFwupFile
[NM_Error](%s) %05d: 3rd firmware os error! offset:0x%x size:%d,char=%c s1:%s
[NM_Error](%s) %05d: 3rd firmware os error! offset:%d size:%d,char=%c
[NM_Error](%s) %05d: 3rd firmware product name error! offset:%d size:%d,char=%c
[NM_Error](%s) %05d: parse 3rd firmware product name error! %d %s
3rd product name NOT match!!! [%s]vs[%s]
[NM_Error](%s) %05d: parse 3rd firmware product name error!
[NM_Error](%s) %05d: 3rd firmware product version error! %s
[NM_Error](%s) %05d: parse 3rd firmware product ver error! %d %d %d
[NM_Error](%s) %05d: 3rd product ver NOT match!!! [%08x]vs[%08x]
[NM_Error](%s) %05d: parse 3rd firmware product ver error!
3rd firmware file_len:%d --%d
3rd firmware file len error!
[NM_Error](%s) %05d: 3rd Firmware check product info error!
[NM_Error](%s) %05d: 3rd Firmware check PTN error!
check 3rd firmware ok!
try to check openwrt firmware...
Check openwrt firmware OK.
[utilities_error: %s:%d]Check openwrt firmware failed!!
nm_fwup_check3rdUpgradeFile
check3rdFirmwareProdInfo
check3rdFirmwarePTN
nm_fwup_upgrade3rdFwupFile
update3rdDataToNvram
```
