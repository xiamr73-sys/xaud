/*  --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : GPIO.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-11
    Description    : This file contains .C file function used for Motor Control.
    ----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
    ------------------------------------------------------------------------------------------------- */
#include "Myproject.h"


/*  -------------------------------------------------------------------------------------------------
    Function Name : void GPIO_Init(void)
    Description   : GPIO初始化配置,可将I/O口配置成输入或输出模式，上拉还是不上拉，模拟输出还是数字输出
    Input         : 无
    Output                :   无
    -------------------------------------------------------------------------------------------------*/

void GPIO_Init(void)
{
    ClrBit(P0_OE, P01);
    SetBit(P0_PU, P01);
    
    SetBit(P0_OE, P00);
    SetBit(P0_PU, P00);
    
    ClrBit(P1_OE, P11);
    SetBit(P1_PU, P11);
	
	SetBit(P1_OE, P12);
    SetBit(P1_PU, P12);
	GP12 = 0;
    
    /* HALL IO */    
    SetBit(P4_OE, P44);
    ClrBit(P4_PU, P44);
    GP44 = 1;
	
		SetBit(P1_OE, P15);
    SetBit(P1_PU, P15);
		GP15 = 0;
    
    ClrBit(P4_OE, P42);
    SetBit(P4_PU, P42);
    
    ClrBit(P3_OE, P37);
    ClrBit(P3_PU, P37);
    
//    SetBit(P0_OE, P05);
//    SetBit(P0_PU, P05);
}

