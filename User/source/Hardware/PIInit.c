/*  --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : PIInit.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-11
    Description    : This file contains PI initial function used for Motor Control.
    ----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
    ------------------------------------------------------------------------------------------------- */
/* Includes -------------------------------------------------------------------------------------*/
#include "Myproject.h"
//void PI_Init(void)
//{
//    PI0_KP  = SKP;
//    PI0_KI  = SKI;
//    PI0_UKH = 0;
//    PI0_UKL = 0;
//    PI0_EK  = 0;
//    PI0_EK1 = 0;
//    PI0_UKMAX = SOUTMAX;
//    PI0_UKMIN = SOUTMIN;
//    SetBit(PI_CR , PI0STA);          // Start PI
//    while (ReadBit(PI_CR , PIBSY));
//}

//void PI_Init(void)
//{
//    PI1_KP  = SKP;
//    PI1_KI  = SKI;
//    PI1_UKH = 0;
//    PI1_UKL = 0;
//    PI1_EK  = 0;
//    PI1_EK1 = 0;
//    PI1_UKMAX = SOUTMAX;
//    PI1_UKMIN = SOUTMIN;
//    SetBit(PI_CR , PI1STA);          // Start PI
//    while (ReadBit(PI_CR , PIBSY));
//}

//void PI_Init(void)
//{
//    PI2_KP  = SKP;
//    PI2_KI  = SKI;
//    PI2_UKH = 0;
//    PI2_UKL = 0;
//    PI2_EK  = 0;
//    PI2_EK1 = 0;
//    PI2_KD = 0x05;
//    PI2_EK2 = 0;
//    PI2_UKMAX = SOUTMAX;
//    PI2_UKMIN = SOUTMIN;
//    SetBit(PI_CR , PI2STA);          // Start PI
//    while (ReadBit(PI_CR , PIBSY));
//}


/*  ----------------------------------------------------------------------------------------------*/
/*  Function Name  : PI_Init
    /*  Description    : PI_Init
    /*  Date           : 2020-09-06
    /*  Parameter      : None
    /*  ----------------------------------------------------------------------------------------------*/
void PI_Init(void)
{
    
    PI2_KP  = SKP;
    PI2_KI  = SKI;
    PI2_UKH = 0;
    PI2_UKL = 0;
    PI2_EK  = 0;
    PI2_EK1 = 0;
    PI2_KD  = SKD;
    PI2_EK2 = 0;
    PI2_UKMAX = SOUTMAX;
    PI2_UKMIN = SOUTMIN;
    SetBit(PI_CR, PI2STA);           // Start PI
    
    while (ReadBit(PI_CR, PIBSY));
  
  
//    PI3_KP  = PosKP;
//    PI3_KI  = PosKI;
//    PI3_UKH = 0;
//    PI3_UKL = 0;
//    PI3_EK  = 0;
//    PI3_EK1 = 0;
//    PI3_KD = PosKD;
//    PI3_EK2 = 0;
//    PI3_UKMAX = POUTMAX;
//    PI3_UKMIN = POUTMIN;
//    SetBit(PI_CR, PI3STA);           // Start PI
//    
//    while (ReadBit(PI_CR, PIBSY));
}
