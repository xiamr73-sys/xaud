/*  --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : AMP.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-11
    Description    : This file contains .C file function used for Motor Control.
    ----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
    ------------------------------------------------------------------------------------------------- */
#include "Myproject.h"

/*  -------------------------------------------------------------------------------------------------
    Function Name : void AMP_Init(void)
    Description   : AMP初始化配置,使能运放电压VHALF，配置运放的电流采样正向输入，反向输入和输出，包括I_BUS,I_U,I_V
                    并使能对应的运放
    Input         : 无
    Output                :   无
    -------------------------------------------------------------------------------------------------*/

void AMP_Init(void)
{
    #if (Shunt_Resistor_Mode == Single_Resistor)
    {
        /*****AMP 端口模拟功能设置******/
        SetBit(P3_AN, P31);             //AMP0 Pin设置为模拟模式  +
        SetBit(P3_AN, P30);             //AMP0 Pin设置为模拟模式  -
        SetBit(P2_AN, P27);             //AMP0 Pin设置为模拟模式  O
        
        SetBit(AMP_CR, AMP0EN);         //AMP0 Enable
    }
    #elif (Shunt_Resistor_Mode == Double_Resistor)
    {
        /*****AMP 端口模拟功能设置******/
        SetBit(P3_AN, P31);             //AMP0 Pin设置为模拟模式  +
        SetBit(P3_AN, P30);             //AMP0 Pin设置为模拟模式  -
        SetBit(P2_AN, P27);             //AMP0 Pin设置为模拟模式  O
    
        SetBit(P1_AN, P16);             //AMP1 Pin设置为模拟模式  +
        SetBit(P1_AN, P17);             //AMP1 Pin设置为模拟模式  -
        SetBit(P2_AN, P20);             //AMP1 Pin设置为模拟模式  O
    
        SetBit(P2_AN, P21);             //AMP2 Pin设置为模拟模式  +
        SetBit(P2_AN, P22);             //AMP2 Pin设置为模拟模式  -
        SetBit(P2_AN, P23);             //AMP2 Pin设置为模拟模式  O
        ClrBit(P2_OE, P23);             //P23_OE需要强制为0，禁止DA1输出至PAD
    
        SetBit(AMP_CR, AMP0EN);         //AMP0 Enable
        SetBit(AMP_CR, AMP1EN);         //AMP1 Enable
        SetBit(AMP_CR, AMP2EN);         //AMP2 Enable
    }
    #elif (Shunt_Resistor_Mode == Three_Resistor)
    {
        SetBit(P3_AN, P31);             //AMP0 Pin设置为模拟模式  +
        SetBit(P3_AN, P30);             //AMP0 Pin设置为模拟模式  -
        SetBit(P2_AN, P27);             //AMP0 Pin设置为模拟模式  O
    
        SetBit(P1_AN, P16);             //AMP1 Pin设置为模拟模式  +
        SetBit(P1_AN, P17);             //AMP1 Pin设置为模拟模式  -
        SetBit(P2_AN, P20);             //AMP1 Pin设置为模拟模式  O
    
        SetBit(P2_AN, P21);             //AMP2 Pin设置为模拟模式  +
        SetBit(P2_AN, P22);             //AMP2 Pin设置为模拟模式  -
        SetBit(P2_AN, P23);             //AMP2 Pin设置为模拟模式  O
        ClrBit(P2_OE, P23);             //P23_OE需要强制为0，禁止DA1输出至PAD
    
        SetBit(AMP_CR, AMP0EN);         //AMP0 Enable
        SetBit(AMP_CR, AMP1EN);         //AMP1 Enable
        SetBit(AMP_CR, AMP2EN);         //AMP2 Enable
    }
    #endif
    

        ClrBit(AMP0_GAIN, AMP0_GAIN2);  //0x80
        ClrBit(AMP0_GAIN, AMP0_GAIN1);  //0x40
        ClrBit(AMP0_GAIN, AMP0_GAIN0);  //0x20
}