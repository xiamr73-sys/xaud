/******************* (C) COPYRIGHT 2019 Fortiortech Shenzhen *******************
* File Name          : FU68xx_4_FLASH.h
* Creat Author       : Any Lin, R&D
* Modify Author      : Any Lin, R&D
* Creat Date         : 2019-06-08
* Modify Date        : 2019-06-11
* Description        :
********************************************************************************
* All Rights Reserved
*******************************************************************************/

#ifndef __FLASH_H__
#define __FLASH_H__

/******************************************************************************///Including Header Files
#include <FU68xx_4_MCU.h>
/******************************************************************************///Define Macro
/******************************************************************************///Define Type

#define     __I     volatile const    /*!< defines 'read only' permissions      */
#define     __O     volatile          /*!< defines 'write only' permissions     */
#define     __IO    volatile          /*!< defines 'read / write' permissions   */

typedef struct
  {
    uint8  *PageAddress;   
    uint8  OffsetAddressCur; 
    uint8  OffsetAddressTar;
    uint8  WriteValue;       
    uint8  ReadValue;       
  }ROM_TypeDef;

extern ROM_TypeDef xdata  Rom;  
extern uint8 Flash_GetAddress(void);
extern uint8 Flash_ErasePageRom(uint8 xdata *FlashAddress);
extern void Flash_KeyWriteValue(uint8 value);
  
/*-------------------------------------------------------------------------------------------------
	Function Name :	uint8 Flash_Sector_Erase(uint8 xdata *FlashAddress)
	Description   :	扇区自擦除: 指定将要擦除的Flash扇区，每个扇区128Byte，共128个扇区，
									扇区0~127对应Flash地址0x0000~0x3fff，通过指定Flash地址来指定要擦除
									的Flash地址所在扇区。一次只能擦除一个扇区，自擦除数据为任意值，一定
									要在解锁后才给DPTR赋值。
	Input         :	FlashAddress--Flash自擦除扇区内任意地址
  Output				:	0--Flash自擦除成功，1--Flash自擦除失败
-------------------------------------------------------------------------------------------------*/
extern uint8 Flash_Sector_Erase(uint8 xdata *FlashAddress);

/*-------------------------------------------------------------------------------------------------
	Function Name :	uint8 Flash_Sector_Write(uint8 xdata *FlashAddress, uint8 FlashData)
	Description   :	Flash自烧写: 对扇区预编程和自擦除后，可以对扇区内的地址进行Flash烧写，
                  一次烧写一个byte,一定要在解锁后才给DPTR赋值
	Input         :	FlashAddress--Flash烧写地址
									FlashData--Flash烧写数据
  Output				:	0--Flash自烧写成功，1--Flash自烧写失败
-------------------------------------------------------------------------------------------------*/
extern uint8 Flash_Sector_Write(uint8 xdata *FlashAddress, uint8 FlashData);
#endif

