/*  --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : FLASH.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-11
    Description    : This file contains .C file function used for Motor Control.
    ----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
    ------------------------------------------------------------------------------------------------- */
/******************************************************************************///Including Header Files
#include "Myproject.h"
/******************************************************************************///Define Macro


ROM_TypeDef xdata  Rom;

uint8 Flash_GetAddress(void);
uint8 Flash_ErasePageRom(uint8 xdata *FlashAddress);
//void Flash_KeyWriteValue(uint8 *value, uint16 FlashAddress , uint8 length);


uint8 Flash_Sector_Erase(uint8 xdata *FlashAddress)
{
    bool TempEA;

    TempEA = EA;
    EA = 0;                            //Flash自擦除前先关总中断

    if(FlashAddress < 0x3f80)          // 不擦除最后一个扇区,0X3F80~0X3FFF
    {
        FLA_CR = 0x03;                 //使能自擦除
        FLA_KEY = 0x5a;
        FLA_KEY = 0x1f;                //flash预编程解锁
        _nop_();
        *FlashAddress = 0xff;          //写任意数据
        FLA_CR = 0x08;                 //开始预编程，完成后Flash再次上锁
    }

    EA = TempEA;                       //Flash自擦除后总中断恢复 

    if(ReadBit(FLA_CR, FLAERR))
    {
        return 1;
    }
    else
    {
        return 0;
    }
}

/*-------------------------------------------------------------------------------------------------
    Function Name : uint8 Flash_Sector_Write(uint8 xdata *FlashAddress, uint8 FlashData)
    Description   : Flash自烧写: 对扇区预编程和自擦除后，可以对扇区内的地址进行Flash烧写，
                    一次烧写一个byte,一定要在解锁后才给DPTR赋值
    Input         : FlashAddress--Flash烧写地址
                    FlashData--Flash烧写数据
    Output        : 0--Flash自烧写成功，1--Flash自烧写失败
-------------------------------------------------------------------------------------------------*/
uint8 Flash_Sector_Write(uint8 xdata *FlashAddress, uint8 FlashData)
{
    bool TempEA;

    TempEA = EA;                       //Flash自烧写前先关总中断
    EA = 0;

  if(FlashAddress < 0x3f80)            // 不编程最后一个扇区,0X3F80~0X3FFF
    {
        FLA_CR = 0x01;                 // 使能Flash编程
        FLA_KEY = 0x5a;
        FLA_KEY = 0x1f;                // flash预编程解锁
        _nop_();
        *FlashAddress = FlashData;     // 写编程数据
        FLA_CR = 0x08;                 // 开始预编程，完成后Flash再次上锁
    }

    EA = TempEA;                       //Flash自烧写后总中断恢复 

    if(ReadBit(FLA_CR, FLAERR))
    {
        return 1;
    }
    else
    {
        return 0;
    }
    EA = EA;
}

/*-------------------------------------------------------------------------------------------------
	Function Name :	void Flash_GetAddress(void)
	Description   :	读取Flash当前地址中的值
	Input         :	null
  Output				: null
-------------------------------------------------------------------------------------------------*/
//uint8 Flash_GetAddress(void)
//{
//  uint8 i;
//  __IO uint8 tevalue = 0;        //临时变量
//  __IO uint8 revalue = 0;        //返回值

//  revalue = 0;
//  Rom.PageAddress = STARTPAGEROMADDRESS;
//  
//  tevalue = *(uint8 code *)Rom.PageAddress;
//  
//  while(tevalue != 0x7F)
//  {
//    Rom.PageAddress = Rom.PageAddress + 0x80; 
//    tevalue = *(uint8 code *)Rom.PageAddress;
//    
//    if(Rom.PageAddress > 0x3F00)
//    {
//      Rom.PageAddress = STARTPAGEROMADDRESS;        
//      revalue = 1;
//      Rom.OffsetAddressCur = 0;
//      Rom.OffsetAddressTar = Rom.OffsetAddressCur + 1;
//      Flash_Sector_Write(Rom.PageAddress,0X7F); 
//      tevalue = 0x7F;
//    }      
//  }

//  for(i = 0; i < 128;i++)
//  {
//    tevalue = *(uint8 code *)(Rom.PageAddress + i);
//    if(tevalue > 0)
//    {
//      Rom.OffsetAddressCur = i;
//      Rom.OffsetAddressTar = Rom.OffsetAddressCur + 1;
//      revalue = tevalue;
//    }
//  }

//  return revalue;
//}


uint8 Flash_ErasePageRom(uint8 xdata *FlashAddress)
{
    bool TempEA;

    TempEA = EA;
    EA = 0;

    if(FlashAddress < 0x3f80)       // 不擦除最后一个扇区
    {
        FLA_CR = 0x03;                                   //使能自擦除
        FLA_KEY = 0x5a;
        FLA_KEY = 0x1f;                                   //flash预编程解锁
        _nop_();
        *FlashAddress = 0xff;                   //写任意数据
        FLA_CR = 0x08;                                   //开始预编程，完成后Flash再次上锁
    }

    EA = TempEA;
    
    if(ReadBit(FLA_CR, FLAERR))
    {
        return 0;
    }
    else
    {
        return 1;
    }
}

void Write_Bytes_To_Flash(uint16 FlashAddress, uint8 *Buff, uint8 length)
{                      

    uint16 i;
    uint8 FlashData = 0;
    uint8 sucess=1,sucess_temp=1;
    for (i = 0; i < length; i++)
    {
        FlashData = *Buff;
        sucess_temp=Flash_Sector_Write((FlashAddress + i), FlashData); //注意此处修改了原函数，返回值1成功
        sucess= sucess & sucess_temp; //有1个0就不成功
        Buff++;
    }
    
                                                                   //读出有效数据
}

