/*  --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : TIMER.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-11
    Description    : This file contains .C file function used for Motor Control.
    ----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
    ------------------------------------------------------------------------------------------------- */
#include "Myproject.h"

/*---------------------------------------------------------------------------*/
/*  Name     :   void Timer1_Init(void)
    /* Input    :   NO
    /* Output   :   NO
    /* Description: Timer1的参数设置
    /*---------------------------------------------------------------------------*/
/* TIM1捕获中断定时器 */
void TIM1_HALL_Init(void)
{
    /* 禁用定时器 */
    ClrBit(TIM1_CR0, T1BCEN);

    /* 定时器分频 */
    SetReg(TIM1_CR3, T1PSC2 | T1PSC1 | T1PSC0, T1PSC2 |T1PSC1| T1PSC0);
  
    /* 基本定时器计数值及重载值 */
    TIM1__BARR  = 60000;
    TIM1__BCNTR = 0;

    //CMP_CR4  FAEN 使能后，TIM1_CR3 的 T1INM 和 CMP_SAMR 的参数均扩大 4 倍
    SetBit(CMP_CR4, FAEN);
    
    /* HALL输入滤波 */
    SetReg(TIM1_CR3, T1INM1 | T1INM0, T1INM1 | T1INM0);  // 96x41.67ns = 4us滤波时长。
  
    /* 输入源选择 */
    ClrBit(TIM1_CR3, T1TIS1 | T1TIS0);
    ClrBit(CMP_CR1, HALLSEL);
  
    /* 触发极性 */
    SetBit(TIM1_DBR7, T1CPE2 | T1CPE1 | T1CPE0); // 三相双跳变沿
//    SetBit(TIM1_DBR6, T1CPE2 | T1CPE1 | T1CPE0); // 三相双跳变沿
//    SetBit(TIM1_DBR5, T1CPE2 | T1CPE1 | T1CPE0); // 三相双跳变沿
//    SetBit(TIM1_DBR4, T1CPE2 | T1CPE1 | T1CPE0); // 三相双跳变沿
//    SetBit(TIM1_DBR3, T1CPE2 | T1CPE1 | T1CPE0); // 三相双跳变沿
//    SetBit(TIM1_DBR2, T1CPE2 | T1CPE1 | T1CPE0); // 三相双跳变沿
//    SetBit(TIM1_DBR1, T1CPE2 | T1CPE1 | T1CPE0); // 三相双跳变沿
    
    TIM1_CR4 = 7;
      
    /* 设置事件复位源 */
    SetBit(TIM1_CR2, T1BRS);  // 位置检测复位
    
    /* 开启位置检测中断 */
    SetBit(TIM1_IER, T1PDIE);  

    PTIM11 = 1;
    PTIM10 = 1;
    /*  开定时器上溢中断 */
    ClrBit(TIM1_IER, T1BOIE);
    
    /* 使能定时器 */
    SetBit(TIM1_CR0, T1BCEN);
  
    /* 清除中断标志位 - 初始化 */
    ClrBit(TIM1_SR, T1BOIF | T1ROIF | T1WTIF | T1PDIF | T1BDIF);
    

}
/*---------------------------------------------------------------------------*/
/*  Name     :   void Timer2_Init(void)
    /* Input    :   NO
    /* Output   :   NO
    /* Description: Timer2的参数设置
    /*---------------------------------------------------------------------------*/
void Timer2_Init(void)
{
    SetBit(PH_SEL, T2SEL);           //P10
    SetBit(PH_SEL, T2SSEL);          //P07
    ClrBit(TIM2_CR0, T2PSC2);        //计数器时钟分频选择
    ClrBit(TIM2_CR0, T2PSC1);        //000-->24M        001-->12M       010-->6M    011-->3M
    ClrBit(TIM2_CR0, T2PSC0);        //100-->1.5M   101-->750K      110-->375K  111-->187.5K
    ClrBit(TIM2_CR0, T2OCM);
    SetBit(TIM2_CR0, T2IRE);         //比较匹配中断/脉宽检测中断0-->Disable  1-->Enable
    ClrBit(TIM2_CR0, T2CES);
    ClrBit(TIM2_CR1, T2IPE);         //输入Timer PWM周期检测中断使能 0-->Disable  1-->Enable
    ClrBit(TIM2_CR1, T2IFE);         //计数器上溢中断使能 0-->Disable  1-->Enable
    ClrBit(TIM2_CR1, T2FE);          //输入噪声滤波使能，小于4个时钟周期脉宽滤除
    ClrBit(TIM2_CR1, T2DIR);         //QEP&ISD&步进模式专用：当前的方向 0-->正向  1-->反向
    TIM2__DR = 1200;
    TIM2__ARR = 2400;
    ClrBit(TIM2_CR0, T2MOD1);        //00-->输入Timer模式           01-->输出模式
    SetBit(TIM2_CR0, T2MOD0);        //10-->输入Counter模式         11-->QEP&ISD&步进模式
    SetBit(TIM2_CR1, T2CEN);         //TIM2使能   0-->Disable  1-->Enable
}

void Timer2_QEP_Init(void)
{
	SetBit(PH_SEL , T2SEL);	    //P10
	SetBit(PH_SEL , T2SSEL);	  //P07	
	
////	ClrBit(TIM2_CR0 , T2PSC2);	//计数器时钟分频选择  //001
////	ClrBit(TIM2_CR0 , T2PSC1);	//000-->24M		001-->12M		010-->6M	011-->3M
////	SetBit(TIM2_CR0 , T2PSC0);	//100-->1.5M	101-->750K		110-->375K	111-->187.5K
	
		ClrBit(TIM2_CR0 , T2PSC2);	//计数器时钟分频选择  //001
	SetBit(TIM2_CR0 , T2PSC1);	//000-->24M		001-->12M		010-->6M	011-->3M
	SetBit(TIM2_CR0 , T2PSC0);	//100-->1.5M	101-->750K		110-->375K	111-->187.5K
	
	ClrBit(TIM2_CR0 , T2OCM);
	
	ClrBit(TIM2_CR0 , T2IRE);	// QEP模式方向改变中断使能
	ClrBit(TIM2_CR0 , T2CES);	// QEP模式 外部中断1(零点)清零脉冲计数器使能
	
	#if (Speed_Method ==  T_Method)	

	ClrBit(TIM2_CR1 , T2IPE);	//输入有效边沿变化使能 0-->Disable  1-->Enable
	SetBit(TIM2_CR1 , T2IFE);	//计数器上溢中断使能 0-->Disable  1-->Enable
	
	#endif
	
	SetBit(TIM2_CR1 , T2FE);	//输入噪声滤波使能，小于4个时钟周期脉宽滤除 4*41.67ns = 166.67ns
	ClrBit(TIM2_CR1 , T2DIR);	//QEP&ISD&步进模式专用：当前的方向 0-->正向	1-->反向	
	
	
#if (Speed_Method ==  T_Method)	
	
	PTIM21 = 1;
	PTIM20 = 0;// TIM2/2中断优先级别为2

#endif
//	TIM2__DR = 1200;
//	TIM2__ARR = 2400;
	
    SetBit(TIM2_CR0 , T2MOD1);	//00-->输入Timer模式  			01-->输出模式
	 SetBit(TIM2_CR0 , T2MOD0);	//10-->输入Counter模式  		11-->QEP&ISD&步进模式
	
    SetBit(TIM2_CR1 , T2CEN);	//TIM2使能	0-->Disable  1-->Enable
    
}
/*---------------------------------------------------------------------------*/
/*  Name     :   void Timer3_Init(void)
    /* Input    :   NO
    /* Output   :   NO
    /* Description: Timer3的参数设置
    /*---------------------------------------------------------------------------*/
void Timer3_Init(void)
{
    SetBit(PH_SEL, T3SEL);            //Timer3端口使能
    ClrBit(PH_SEL1, T3CT);            //默认端口为P11,功能转移后为P01,需TIMER4转移到P00
    SetBit(TIM3_CR0, T3PSC2);         //计数器时钟分频选择
    ClrBit(TIM3_CR0, T3PSC1);         //000-->24M       001-->12M       010-->6M    011-->3M
    SetBit(TIM3_CR0, T3PSC0);         //100-->1.5M  101-->750K      110-->375K  111-->187.5K
    ClrBit(TIM3_CR0, T3OCM);
    ClrBit(TIM3_CR0, T3IRE);          //比较匹配中断/脉宽检测中断0-->Disable  1-->Enable
    ClrBit(TIM3_CR0, T3OPM);          //0-->计数器不停止      1-->单次模式
    SetBit(TIM3_CR1, T3IPE);          //输入Timer PWM周期检测中断使能 0-->Disable  1-->Enable
    SetBit(TIM3_CR1, T3IFE);          //计数器上溢中断使能 0-->Disable  1-->Enable
    ClrBit(TIM3_CR1, T3NM1);          //输入噪声脉宽选择
    ClrBit(TIM3_CR1, T3NM0);          //00-->不滤波  01-->4cycles    10-->8cycles  11-->16cycles
    //  TIM3__DR = 1200;
    //  TIM3__ARR = 65535;
    ClrBit(TIM3_CR0, T3MOD);           //0-->Timer模式       1-->输出模式
    SetBit(TIM3_CR1, T3EN);            //TIM3使能    0-->Disable  1-->Enable
}
/*---------------------------------------------------------------------------*/
/*  Name     :   void Timer4_Init(void)
    /* Input    :   NO
    /* Output   :   NO
    /* Description: Timer4的参数设置
    /*---------------------------------------------------------------------------*/
void Timer4_Init(void)
{
    SetBit(PH_SEL, T4SEL);               //Timer4端口使能
    SetBit(PH_SEL1, T4CT);               //默认端口为P01,功能转移后为P00
    //  ClrBit(TIM4_CR0 , T4PSC2);       //计数器时钟分频选择
    //  ClrBit(TIM4_CR0 , T4PSC1);       //000-->24M        001-->12M       010-->6M    011-->3M
    //  ClrBit(TIM4_CR0 , T4PSC0);       //100-->1.5M   101-->750K      110-->375K  111-->187.5K
    SetReg(TIM4_CR0, T3PSC2 | T3PSC1 | T3PSC0, T3PSC2);
    SetBit(TIM4_CR0, T4OCM);
    ClrBit(TIM4_CR0, T4IRE);             //比较匹配中断/脉宽检测中断0-->Disable  1-->Enable
    ClrBit(TIM4_CR0, T4OPM);             //0-->计数器不停止       1-->单次模式
    ClrBit(TIM4_CR1, T4IPE);             //输入Timer PWM周期检测中断使能 0-->Disable  1-->Enable
    ClrBit(TIM4_CR1, T4IFE);             //计数器上溢中断使能 0-->Disable  1-->Enable
    ClrBit(TIM4_CR1, T4NM1);             //输入噪声脉宽选择
    ClrBit(TIM4_CR1, T4NM0);             //00-->不滤波   01-->4cycles  10-->8cycles  11-->16cycles
    TIM4__ARR = 65535;
    SetBit(TIM4_CR0, T4MOD);             //0-->Timer模式  1-->输出模式
    SetBit(TIM4_CR1, T4EN);              //TIM4使能   0-->Disable  1-->Enable
}
