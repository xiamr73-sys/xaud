/*  --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : Interrupt.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-10
    Description    : This file contains .C file function used for Motor Control.
    ----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
    ------------------------------------------------------------------------------------------------- */
#include "MyProject.h"

uint16 xdata spidebug[4] = { 0 };
//uint8 Learn_Data[2]={0};

extern  int32 speedRef;

extern  uint8 SYST_Times;
uint8 Learn_Data[2]={0};

/*  -------------------------------------------------------------------------------------------------
    Function Name  : EXTI_INT
    Description    : EXTI0 INT，Z
    Date           : 2020-04-10
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */
void EXTI_INT(void) interrupt 1  //LVW & TSD interrupt
{
    if ((mcQEP.ZSaveFlag == 0) && (mcFocCtrl.SoftStart_Flag))
    {
        mcQEP.ZSaveFlag = 1;
        mcQEP.ZCNTR = mcQEP.ZeroCntr;
		mcQEP.ZeroCntr = mcQEP.CntrSumReal;
    }
    
    IF0 = 0;
}


extern uint16 lightSwitch ;


void TIM1_INT(void) interrupt 5
{
    if (ReadBit(TIM1_SR, T1BOIF))
    {
        ClrBit(TIM1_SR, T1BOIF);
    }
    
    if (ReadBit(TIM1_SR, T1PDIF))
    {
        ClrBit(TIM1_SR, T1PDIF);
    }
    
    if (ReadBit(TIM1_SR, T1BDIF))
    {
        ClrBit(TIM1_SR, T1BDIF);
    }
}


/*  -------------------------------------------------------------------------------------------------
    Function Name  : DRV_ISR
    Description    : FOC中断(Drv中断),每个载波周期执行一次，用于处理响应较高的程序，中断优先级第二。DCEN开了就会产生中断。
    Date           : 2020-04-10
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */

void DRV_ISR(void) interrupt 3 //测试用时间   M法%78占空比    T法%67
{
    int32 tempCntrSum;
    static uint16 idata PeriodTime;
	  int16  *aa;
    
    if (ReadBit(DRV_SR, FGIF))
    {
        ClrBit(DRV_SR, FGIF);
    }
    
    if (ReadBit(DRV_SR, DCIF))    // 比较中断
    {
        	 
        mcQEP.CntrOld    = mcQEP.Cntr;
        mcQEP.Cntr       = TIM2__CNTR;   // 计数值
        mcQEP.PeriodTime = TIM2__ARR;
        mcQEP.CntrErr = mcQEP.Cntr - mcQEP.CntrOld;
			

				if(UqPo.UqPoaiFlag == 0)
				{
					UqPo.ThetaN = FOC__THETA;
					UqPo.IQN = FOC_IQREF;
				}
        
        if (mcQEP.CntrErr < 0)
        {
            if (mcQEP.Cntr > mcQEP.CntrOld)
            {
                mcQEP.Cycle--;
							
            }
            
            mcQEP.Dir = 1;
        }
        
        if (mcQEP.CntrErr > 0)
        {
            if (mcQEP.Cntr < mcQEP.CntrOld)
            {
                mcQEP.Cycle++;
            }
            
            mcQEP.Dir = 0;
        }
					
				 *(int16 *)(&tempCntrSum) = mcQEP.Cycle;
    
        mcQEP.CntrSumReal =  tempCntrSum + mcQEP.Cntr;

        mcQEP.CntrSum = (Learn.AngleBase << 1) - mcQEP.CntrSumReal - Learn.AngleBias;
        
        if (mcQEP.PeriodTime <= QEPPluseMinTime)
        {
            mcQEP.PeriodTime = QEPPluseMinTime + 1;
        }
        
        MuiltS_L_MDU(mcQEP.Cntr, ETHETA_PER_PLASE, mcQEP.Theta);

        #if (Speed_Method == T_Method)
        {

            DivQ_L_MDU(mcQEP.SpeedCalBaseH, mcQEP.SpeedCalBaseL, mcQEP.PeriodTime, mcQEP.AbsSpeed);
            mcQEP.SpeedAvg = mcQEP.AbsSpeed;
            
            if (mcQEP.OverFlowFlag)
            {
                mcQEP.AbsSpeed = 0;
            }
            
            if (mcQEP.DirOld != mcQEP.Dir) // 两次方向不同，速度给 0
            {
                mcQEP.AbsSpeed = 0;
                mcQEP.DirOld   = mcQEP.Dir;
            }
            else // 若两次方向相同计算速度
            {
                if (mcQEP.Dir)
                {
                    mcQEP.Speed =  -  mcQEP.AbsSpeed;
                }
                else
                {
                    mcQEP.Speed =     mcQEP.AbsSpeed;
                }
            }
            
            LPF_MDU(mcQEP.Speed, 5, mcFocCtrl.SpeedFlt, mcFocCtrl.SpeedFlt_LSB);
            
            if (mcFocCtrl.SpeedFlt < 2 && mcFocCtrl.SpeedFlt > -2)
            { mcFocCtrl.SpeedFlt = 0; }
        }
        #elif (Speed_Method == M_Method)
        {
            /*************************2K的M法测速*******************************/
            mcQEP.M_CNT++;
        
            if (mcQEP.M_CNT == 8)
            {
                mcQEP.M_CNT = 0;
                mcQEP.CntrM = mcQEP.Cntr;
                mcQEP.PosDiff =  mcQEP.CntrM - mcQEP.CntrOldM;
                mcQEP.PosDiffSum += mcQEP.PosDiff - mcQEP.PosDiffArray[mcQEP.ArrayPointer];
                mcQEP.PosDiffArray[mcQEP.ArrayPointer] =       mcQEP.PosDiff;
                mcQEP.ArrayPointer++;
        
                if (mcQEP.ArrayPointer >= 4)
                {
                    mcQEP.ArrayPointer = 0;
                }
								
								
							mcQEP.PosDiffSumTemp = mcQEP.PosDiffSum;
              if (mcQEP.PosDiffSumTemp>200)
							{
								mcQEP.PosDiffSumTemp =200;
							}
							if (mcQEP.PosDiffSumTemp<-200)
							{
								mcQEP.PosDiffSumTemp= -200;
							}
                MuiltS_L_MDU(mcQEP.PosDiffSumTemp>>1, 375, mcQEP.SpeedM);
                mcQEP.CntrOldM = mcQEP.CntrM;
                LPF_MDU(mcQEP.SpeedM, 150, mcQEP.SpeedMFlt, mcQEP.SpeedMFlt_LSB);
        
                if (mcQEP.SpeedMFlt < 2 && mcQEP.SpeedMFlt > -2)
                { mcQEP.SpeedMFlt = 0; }
            }
        }
        #endif
        
        if ((mcState == mcRun) && (mcFocCtrl.ThetaIQ_SOURCE == 0))
        {

            if (GP42)
            {
							if(UqPo.PosiLockFlag == 0)
							{
                FOC__THETA  = mcQEP.Theta;
							}

            }
            else 
            {
                FOC__THETA += 5;
							GP15 = 1;
            }
        }
/*----------------------------------------切强拖与预定位--------------------------------------*/
				if(mcFocCtrl.Timedelay >= 5000)
				{
					if((mcFocCtrl.PosiErr <= 700) && (mcFocCtrl.PosiErr >= -700))
					{
						mcFocCtrl.ThetaIQ_SOURCE = 1;
						mcFocCtrl.UQTurnFlag = 1;
					}
				}
				if(mcFocCtrl.UQTurnFlag)
				{
					GP12 = ~GP12;
					FOC_IQREF = 0;
					SetBit(FOC_CR2, UDD);
					SetBit(FOC_CR2, UQD);
					FOC__UQ = UD_Align_Duty_Max;
					FOC__UD = 0;
					FOC__THETA += 3;
					DRV_CMR |= 0x3F;                         // U、V、W相输出
					MOE = 1;
                    if((mcFocCtrl.PosiErr <= 80) && (mcFocCtrl.PosiErr >= -80))
                    {
                        FOC__THETA = UqPo.ThetaN;
                        FOC__UD = UD_Align_Duty_Max;
                        FOC__UQ = 0;
                        mcFocCtrl.UQTurnFlag = 0;
                        mcFocCtrl.UQLockFlag = 1;
                    }
                }
                else
                {
                    if(mcFocCtrl.UQLockFlag)
                    {
                        SetBit(FOC_CR2, UDD);
                        ClrBit(FOC_CR2, UQD);
                        FOC__UQ = 0;
                        FOC__UD = UD_Align_Duty_Max;
                        FOC__THETA = UqPo.ThetaN;
                        DRV_CMR |= 0x3F;
                        MOE = 1;
                    }
                    else
                    {
                        ClrBit(FOC_CR2, UDD);
                        ClrBit(FOC_CR2, UQD);
                    }
                }
/*-----------------------------------------------------------------------------------------*/				
				
        #if (DBG_MODE == SPI_DBG_SW)            // 软件调试模式
        {
            spidebug[0] = FOC__THETA;//_Q15(Angle /180.0);//mcQEP.Cycle;
            spidebug[1] = FOC__THETA;//mcQEP.CntrSumReal;
            spidebug[2] = mcFocCtrl.LreanAngleFlt;//mcQEP.Theta;
            spidebug[3] = mcQEP.CntrSumReal;//mcSP.PulsesNum;
        }
        #endif
        SetReg(DRV_SR, 0xFF, SYSTIE | DCIM1 | SYSTIF);
    }
}

void TIM2_INT(void) interrupt 4
{
    if (ReadBit(TIM2_CR1, T2IR))
    {
        ClrBit(TIM2_CR1, T2IR);
    }
    
    if (ReadBit(TIM2_CR1, T2IP))
    {
        mcQEP.OverFlowFlag++;
        
        if (mcQEP.OverFlowFlag >= 3) //代表静止之后连续两次跳变
        {
            mcQEP.OverFlowFlag = 0;
            ClrBit(TIM2_CR1, T2IPE);
        }
        
        ClrBit(TIM2_CR1, T2IP);
    }
    
    if (ReadBit(TIM2_CR1, T2IF))   // 溢出中断,用于判断静止,时间为349ms。
    {
        //        if(mcQEP.OverFlowFlag<10)
        //            mcQEP.OverFlowFlag++;
        mcQEP.OverFlowFlag = 1;
        SetBit(TIM2_CR1, T2IPE);
        ClrBit(TIM2_CR1, T2IF);
    }
}


/*  -------------------------------------------------------------------------------------------------
    Function Name  : CMP_ISR
    Description    : CMP0/1/2：顺逆风判断
    Date           : 2020-04-10
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */
void CMP_ISR(void) interrupt 7
{
    if (ReadBit(CMP_SR, CMP0IF) || ReadBit(CMP_SR, CMP1IF) || ReadBit(CMP_SR, CMP2IF)) //当检测到比较器中断时
    {
        ClrBit(CMP_SR, CMP0IF | CMP1IF | CMP2IF);
    }
}


/*  -------------------------------------------------------------------------------------------------
    Function Name  : SYStick_INT
    Description    : 1ms定时器中断（SYS TICK中断），用于处理附加功能，如控制环路响应、各种保护等。中断优先级低于FO中断和FOC中断。
    Date           : 2020-04-10
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */
uint32 Timex = 0;


void SYStick_INT(void) interrupt 10  //2K的执行周期  %55
{
    static uint8  SYST_Cnt;
    
    if (ReadBit(DRV_SR, SYSTIF))          // SYS TICK中断
    {
			mcQEP.g1msflg++;
        //          GP05 = 1;
        SetBit(ADC_CR, ADCBSY);           //使能ADC的DCBUS采样
	
        
        if (Uart.EnableTimeCnt == 1)
        {
            SYST_Cnt++;//
            
            if (SYST_Cnt == SYST_Times) //2次1ms
            {
                SYST_Cnt = 0;
                Uart.Go_Time++;
            }
        }
        if(mcFocCtrl.Timedelay <= 10000)
				{
					mcFocCtrl.Timedelay++;
				}
				
        /* -----环路响应，如速度环、转矩环、功率环等----- */
        Speed_response();  //152us
        LPF_MDU(ADC14_DR, 100, mcFocCtrl.mcDcbusFlt, mcFocCtrl.mcDcbusFlt_LSB);
        mcFocCtrl.mcDcbusFlt = ADC14_DR;
        Fault_Detection(); //52us
        //Fault_Communication();
        GP00 = ~GP00;
        /* ****电机状态机的时序处理**** */
        if (mcFocCtrl.State_Count > 0)
        {
            mcFocCtrl.State_Count--;
        }
        if (mcFocCtrl.SoftStart_Flag == 0)
        {
            mcFocCtrl.SoftStart_Count++;
            if (mcFocCtrl.SoftStart_Count > 200) 
            {
                mcQEP.ZSaveFlag = 0;
                mcFocCtrl.SoftStart_Flag = 1;
            }
        }
        if (GP42 == 0)
        {           
            if (mcFocCtrl.Lrean_State == 1)
            {

                mcFocCtrl.Lrean_State = 0;
              
                Learn_Data[0] = mcFocCtrl.LreanAngle >> 8;
                Learn_Data[1] = mcFocCtrl.LreanAngle;
                EA = 0;
                Flash_ErasePageRom(STARTPAGEROMADDRESS);
                
                Flash_Sector_Write(STARTPAGEROMADDRESS, Learn_Data[0]);
                Flash_Sector_Write(STARTPAGEROMADDRESS+1, Learn_Data[1]);
                EA = 1;            
            }
        } 

        /***********测试转动*********************/
        #if OPEN_TEST
        
        if (mcFocCtrl.CtrlMode == 1 && Power.Reign == 1)
        {
            Timex++;
            
            if (Timex == 80000)
            {
                Timex = 0;
                mcSP.PulsesNum      = P_Value(134);
                Speed_Handle(0X18);
            }
            
            if (Timex == 60000)
            {
                mcSP.PulsesNum      = P_Value(10) ;
                Speed_Handle(SpeedLevel);
            }
            else if (Timex == 40000)
            {
                mcSP.PulsesNum      = P_Value(134);
                Speed_Handle(0X18);
            }
            else if (Timex == 20000)
            {
                mcSP.PulsesNum      = P_Value(210);
                Speed_Handle(0X18);
            }
        }
        
        #endif
        SetReg(DRV_SR, 0xFF, SYSTIE | DCIM1 | DCIF);
    }
}
/*  -------------------------------------------------------------------------------------------------
    Function Name  : CMP3_INT
    Description    : CMP3：硬件比较器过流保护，关断输出，中断优先级最高
    Date           : 2020-04-10
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */

void CMP3_INT(void)  interrupt 12
{
    if (ReadBit(CMP_SR, CMP3IF))
    {
        if (mcState != mcPosiCheck)
        {
            FaultProcess();                                                                   // 关闭输出
            mcFaultSource = FaultHardOVCurrent;                                                 // 硬件过流保护
            mcState       = mcFault;
            // 状态为mcFault
        }
        
        ClrBit(CMP_SR, CMP3IF);
    }
}

/*---------------------------------------------------------------------------*/
/*  Name     :   void TIM4_INT(void) interrupt 10
    /* Input    :   NO
    /* Output   :   NO
    /* Description: TIM4会用到FG输出，如果TIM4用作基本定时器需要注意
    /*---------------------------------------------------------------------------*/
//void TIM4_INT(void) interrupt 11
//{
//    /*TIM4 Interrupt*/
//    if (ReadBit(TIM4_CR1, T4IR))
//    {
//        ClrBit(TIM4_CR1, T4IR);
//    }
//
//    if (ReadBit(TIM4_CR1, T4IP)) //周期中断
//    {
//        ClrBit(TIM4_CR1, T4IP);
//    }
//
//    if (ReadBit(TIM4_CR1, T4IF))
//    {
//        ClrBit(TIM4_CR1, T4IF);
//    }
//}

void USART2_INT(void)  interrupt 14
{
    uint8 Uredata = 0;
    
    if (ReadBit(UT2_CR, UT2TI))
    {
        ClrBit(UT2_CR, UT2TI);
        
        if (Uart.SendCnt < Uart.T_Len - 1)
        {
            Uart.SendCnt++;
            UART_SendData(Uart.T_DATA[Uart.SendCnt]);
        }
        
        //        if(Uart.T_DATA[Uart.SendCnt] != 0xff)
        //        {
        //            Uart.SendCnt++;
        //            UART_SendData(Uart.T_DATA[Uart.SendCnt]);
        //        }
    }
    
    if (ReadBit(UT2_CR, UT2RI) )
    {
        ClrBit(UT2_CR, UT2RI);
        Uredata = UT2_DR;
        
        switch (Uart.Read_State)
        {
            case 0:
                if (Uredata == 0x81)
                {
                    Uart.R_DATA[Uart.UARxCnt++] = Uredata;
                    Uart.Read_State = 1;
                }
                
                //                else
                //                {
                //                   Uart.UARxCnt = 0;
                //                   Uart.ResponceFlag = 0;
                //                   Uart.Read_State =  0;
                //                   Send_NoActive(); //无效指令 帧头不对
                //                }
                break;
                
            case 1:
                Uart.R_DATA[Uart.UARxCnt++] = Uredata;
                
                if (Uart.UARxCnt >= 20)
                {
                    Uart.UARxCnt = 0;
                    Uart.ResponceFlag = 0;
                    Uart.Read_State =  0;
                }
                
                if (Uredata == 0Xff)//&& Uart.UARxCnt==15)
                {
                    if (Uart.UARxCnt >= 4 && Uart.UARxCnt <= 15)
                    {
                        Uart.UARxCnt = 0;
                        Uart.ResponceFlag = 1;
                        Uart.Read_State =  0;
                    }
                    else
                    {
                        Uart.UARxCnt = 0;
                        Uart.ResponceFlag = 0;
                        Uart.Read_State =  0;
                        Send_NoActive(); //无效指令  长度不对
                    }
                }
                
                break;
                
            default:
                Uart.UARxCnt = 0;
                Uart.ResponceFlag = 0;
                Uart.Read_State =  0;
                break;
        }
    }
}


void TIM3_INT(void) interrupt 9
{
    if (ReadBit(TIM3_CR1, T3IR))
    {
        ClrBit(TIM3_CR1, T3IR);
    }
    
    if (ReadBit(TIM3_CR1, T3IP))//周期中断
    {
        mcPwmInput.TimeDR    = TIM3__DR;
        mcPwmInput.TimeARR        = TIM3__ARR;
        mcPwmInput.PwmUpdateFlag = 1;
        ClrBit(TIM3_CR1, T3IP);
    }
    
    if (ReadBit(TIM3_CR1, T3IF))
    {
        if (ReadBit(P1, PIN1))//PWM 100%输出
        {
            mcPwmInput.TimeDR = 4000;
            mcPwmInput.TimeARR     = 4000;
        }
        else//PWM 为0%
        {
            mcPwmInput.TimeDR = 0;
            mcPwmInput.TimeARR     = 4000;
        }
        
        mcPwmInput.PwmUpdateFlag = 1;
        ClrBit(TIM3_CR1, T3IF);
    }
}
