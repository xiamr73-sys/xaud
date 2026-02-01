/*  --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : CRC.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-11
    Description    : This file contains .C file function used for Motor Control.
    ----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
    ------------------------------------------------------------------------------------------------- */
#include "Myproject.h"


/*  ----------------------------------------------------------------------------------------------*/
/*  Function Name  : CRC_Check
    /*  Description    : CRC16_CCITT_FALSE  硬件实现
    /*  Date           : 2020-09-06
    /*  Parameter      : start_sector: [输入/出]
**           offset_sector: [输入/出]
    /*  ----------------------------------------------------------------------------------------------*/
unsigned short CRC_Check(unsigned char start_sector, unsigned char offset_sector)
{
    unsigned short crcresult = 0x0000;
    unsigned short tempH = 0x00;
    unsigned short tempL = 0x00;
    SetBit(CRC_CR, CRCVAL);         //0-->0x0000  1-->0xffff
    SetBit(CRC_CR, CRCDINI);        //1-->init success
    CRC_BEG = start_sector;     //起始扇区
    CRC_CNT = offset_sector;    //扇区偏移量   0-->1个扇区
    //1个空扇区-->0x41E8     2个空扇区-->0x1634
    //1个0xFF  -->0x5B2F    0x00~0xFF-->0x3FBD
    SetBit(CRC_CR, AUTOINT);        //自动计算使能
    /* ************************************************* */
    SetBit(CRC_CR, CRCPNT);
    tempH = CRC_DR;
    ClrBit(CRC_CR, CRCPNT);
    tempL = CRC_DR;
    crcresult = (unsigned short)(tempH << 8) + tempL;
    return crcresult;
}
