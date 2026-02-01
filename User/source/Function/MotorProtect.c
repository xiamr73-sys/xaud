/* --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : MotorControl.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-10
    Description    : This file contains .C file function used for Motor Control.
----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
------------------------------------------------------------------------------------------------- */
#include <MyProject.h>
extern bool OpenFlag;

/*  -------------------------------------------------------------------------------------------------
    Function Name  : FaultProcess
    Description    : ??????,??FOC??,???????mcFault
    Date           : 2020-04-10
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */
void FaultProcess(void)
{
    if(mcFaultSource != FaultNoSource)
    {
//        ClrBit(DRV_CR, DRVEN);  //Driver Disable
//        ClrBit(DRV_CR, FOCEN);  //FOC Disable
        MOE     = 0;
        _nop_();
    }
    else if(OpenFlag == 0)
    {
        mcState = mcReady;
    }
    else
    {
//        SetBit(DRV_CR, FOCEN);
        MOE  = 1;
        mcState = mcRun;
    }
}


/*  -------------------------------------------------------------------------------------------------
    Function Name  : Fault_OverUnderVoltage
    Description    : 过压欠压保护函数：程序每5ms判断一次，母线电压大于过压保护值时，计数器加一，计数器值超过20次，判断为过压保护，关闭输出;反之，计数器慢慢减
                     同理，欠压保护。
                     电机过欠压保护状态下，母线电压恢复到欠压恢复值以上，过压恢复值以下时，计数器加一，超过200次后，恢复。根据档位信息来决定恢复到哪个状态。
    Date           : 2020-04-10
    Parameter      : h_Fault: [输入/出]
    ------------------------------------------------------------------------------------------------- */
void Fault_OverUnderVoltage(void)
{
//    if (mcFaultDect.UnderVoltageDelayCnt <= 2000) //5s
//        {
//            mcFaultDect.UnderVoltageDelayCnt++;
//        }
//    else 
    if (mcFaultSource == FaultNoSource) //程序无其他保护下
    {
        //过压保护
        if (mcFocCtrl.mcDcbusFlt > OVER_PROTECT_VALUE)   //母线电压大于过压保护值时，计数，超过20次，判断为过压保护，关闭输出;反之，计数器慢慢减
        {
            mcFaultDect.OverVoltDetecCnt++;
            
            if (mcFaultDect.OverVoltDetecCnt > 10) //检测50ms
            {
                mcFaultDect.OverVoltDetecCnt = 0;
                mcFaultSource             = FaultOverVoltage;
//								mcFaultDect.CurrentFlag = 0;
                mcState = mcFault;
            }
        }
        else if (mcFaultDect.OverVoltDetecCnt > 0)
        {
            mcFaultDect.OverVoltDetecCnt--;
        }
        
        //欠压保护
        if (mcFocCtrl.mcDcbusFlt < UNDER_PROTECT_VALUE)
        {
            mcFaultDect.UnderVoltDetecCnt++;
            
            if (mcFaultDect.UnderVoltDetecCnt > 10) //检测50ms
            {
                mcFaultDect.UnderVoltDetecCnt = 0;
                mcFaultSource              = FaultUnderVoltage;
                mcState = mcFault;
            }
        }
        else if (mcFaultDect.UnderVoltDetecCnt > 0)
        {
            mcFaultDect.UnderVoltDetecCnt--;
        }
    }
    
    /*******过压欠压保护恢复*********/
    if ((mcState == mcFault) && ((mcFaultSource == FaultUnderVoltage) || (mcFaultSource == FaultOverVoltage)))
    {
        if ((mcFocCtrl.mcDcbusFlt < OVER_RECOVER_VALUE) && (mcFocCtrl.mcDcbusFlt > UNDER_RECOVER_VALUE))
        {
            mcFaultDect.VoltRecoverCnt++;
            
            if (mcFaultDect.VoltRecoverCnt > 40) //连续检测200ms，若正常则恢复
            {
//                mcState                 = mcReady;
                mcFaultSource           = FaultNoSource;
                mcFaultDect.VoltRecoverCnt = 0;
            }
        }
        else
        {
            mcFaultDect.VoltRecoverCnt = 0;
        }
    }
}

/*  -------------------------------------------------------------------------------------------------
    Function Name  : Fault_Overcurrent
    Description    : 电机运行或者启动时，当三相中某一相最大值大于OverCurrentValue，则OverCurCnt加1。
                     连续累加3次，判断为软件过流保护。执行时间约30.4us。
    Date           : 2020-04-10
    Parameter      : h_Cur: [输入/出]
    ------------------------------------------------------------------------------------------------- */
void Fault_Overcurrent(void)
{
    if ((mcState == mcRun) || (mcState == mcStart))                       // check over current in rum and open mode
    {
        // 此部分既用于软件过流保护，又用于缺相保护
        mcCurVarible.Max_ia = FOC__IAMAX;
        mcCurVarible.Max_ib = FOC__IBMAX;
        mcCurVarible.Max_ic = FOC__ICMAX;
        mcCurVarible.Max_ia = FOC__IAMAX;
        mcCurVarible.Max_ib = FOC__IBMAX;
        mcCurVarible.Max_ic = FOC__ICMAX;
        
        if ((FOC__IAMAX >= OverSoftCurrentValue)
            || (FOC__IBMAX >= OverSoftCurrentValue)
            || (FOC__ICMAX >= OverSoftCurrentValue))
        {
            mcCurVarible.OverCurCnt++;
            
            if (mcCurVarible.OverCurCnt >= 3)
            {
//                mcState = mcFault;
//                mcFaultSource     = FaultSoftOVCurrent;
								mcFaultDect.CurrentFlag = 1;
                mcCurVarible.Max_ia     = 0;
                mcCurVarible.Max_ib     = 0;
                mcCurVarible.Max_ic     = 0;
                mcCurVarible.OverCurCnt = 0;
            }
        }
        else if (mcCurVarible.OverCurCnt > 0)
        {
            mcCurVarible.OverCurCnt--;
        }
    }
}

/*  -------------------------------------------------------------------------------------------------
    Function Name  : Fault_OverCurrentRecover
    Description    : 软硬件过流保护恢复
    Date           : 2020-04-10
    Parameter      : h_Fault: [输入/出]
    ------------------------------------------------------------------------------------------------- */
void Fault_OverCurrentRecover(void)
{
    if ((mcState == mcFault) && ((mcFaultSource == FaultSoftOVCurrent)
            || (mcFaultSource == FaultHardOVCurrent))) //&& (mcProtectTime.CurrentPretectTimes < 5))
    {
        mcFaultDect.CurrentRecoverCnt++;
        
        if (mcFaultDect.CurrentRecoverCnt >= OverCurrentRecoverTime) //200*5=1s
        {
            mcFaultDect.CurrentRecoverCnt = 0;
            mcProtectTime.CurrentPretectTimes++;
//            mcState       = mcReady;
            mcFaultSource = FaultNoSource;
						mcFaultDect.CurrentFlag = 0;
        }
    }
}


/*  -------------------------------------------------------------------------------------------------
    Function Name  : Fault_Stall
    Description    : 堵转保护函数，有三种保护方式，
                   第一种，
                   第二种，电机运行状态下，延迟4s判断，估算速度绝对值超过堵转速度连续5次；
                   第三种，电机运行状态下，当U,V两相电流绝对值大于堵转电流保护值连续6次；
                   当以上三种的任何一种保护触发时，电机停机，程序判断为堵转保护；
                   当堵转保护状态下，U相采集值低于堵转恢复值时，若堵转次数小于或等于堵转重启次数8次，
                   程序延迟mcStallRecover重新启动，进行校准状态。
    Date           : 2020-04-10
    Parameter      : h_Fault: [输入/出]
    ------------------------------------------------------------------------------------------------- */
int16 IQ;
void Fault_Stall(void)
{
    if (mcState == mcRun)
    {
        if (mcFaultDect.StallDelayCnt <= 2000) //5s
        {
            mcFaultDect.StallDelayCnt++;
        }
        else
        {
            IQ = FOC__IQ;
            if((mcFocCtrl.SpeedFlt < Motor_Stall_Min_Speed) && ((IQ > I_Value(0.46)) || (IQ < I_Value(-0.46))))

//          if((mcFocCtrl.SpeedFlt < Motor_Stall_Min_Speed) && ((IQ > I_Value(0.48)) || (IQ < I_Value(-0.48))))
            {
                mcFaultDect.StallDectSpeed++;
              
                if (mcFaultDect.StallDectSpeed >= 100)

//             if (mcFaultDect.StallDectSpeed >= 100)
                {
                    mcFaultDect.StallDectSpeed = 0;
                    mcFaultSource           = FaultStall;
                    mcProtectTime.StallTimes++;
                    mcState = mcFault;
                    mcProtectTime.StallFlag = 1;
                }
            }
            //method 2，判断速度低于堵转最小值或者超过堵转最大值
            else if (mcFocCtrl.SpeedFlt > Motor_Stall_Max_Speed)
            {
                mcFaultDect.StallDectSpeed++;
                
                if (mcFaultDect.StallDectSpeed >= 10)
                {
                    mcFaultDect.StallDectSpeed = 0;
                    mcFaultSource           = FaultStall;
                    mcProtectTime.StallTimes++;
                    mcState = mcFault;
                    mcProtectTime.StallFlag = 2;
                }
            }
            else
            {
                if (mcFaultDect.StallDectSpeed > 0)
                {
                    mcFaultDect.StallDectSpeed--;
                }
            }
          
        }
    }
    
    #if (!StartONOFF_Enable)
    {
        /*******堵转保护恢复*********/
        if ((mcFaultSource == FaultStall) && (mcState == mcFault)) //&& (mcProtectTime.StallTimes <= StallProtectRestartTimes))
        {
            mcFaultDect.StallReCount++;
            
            if (mcFaultDect.StallReCount >= StallRecoverTime)
            {
                mcFaultDect.StallReCount = 0;
                mcFaultSource         = FaultNoSource;
//                mcState               = mcReady;
            }
        }
        else
        {
            mcFaultDect.StallReCount = 0;
        }
    }
    #endif
}

/*  -------------------------------------------------------------------------------------------------
    Function Name  : Fault_phaseloss
    Description    : 缺相保护函数，当电机运行状态下，10ms取三相电流的最大值，
                   1.5s判断各相电流最大值，若存在两相电流值大于一定值，而第三相电流值却非常小，则判断为缺相保护，电机停机；
    Date           : 2020-04-10
    Parameter      : h_Fault: [输入/出]
    ------------------------------------------------------------------------------------------------- */
void Fault_phaseloss(void)
{
    if (mcState == mcRun)
    {
        mcFaultDect.Lphasecnt++;
        
        if (mcFaultDect.Lphasecnt > 100) //100*5=500ms
        {
            mcFaultDect.Lphasecnt = 0;
            
            if (((mcCurVarible.Max_ia > (mcCurVarible.Max_ib * 2)) || (mcCurVarible.Max_ia > (mcCurVarible.Max_ic * 2)))
                && (mcCurVarible.Max_ia > PhaseLossCurrentValue))
            {
                mcFaultDect.AOpencnt++;
            }
            else
            {
                if (mcFaultDect.AOpencnt > 0)
                {
                    mcFaultDect.AOpencnt --;
                }
            }
            
            if (((mcCurVarible.Max_ib > (mcCurVarible.Max_ia * 2)) || (mcCurVarible.Max_ib > (mcCurVarible.Max_ic * 2)))
                && (mcCurVarible.Max_ib > PhaseLossCurrentValue))
            {
                mcFaultDect.BOpencnt++;
            }
            else
            {
                if (mcFaultDect.BOpencnt > 0)
                {
                    mcFaultDect.BOpencnt --;
                }
            }
            
            if (((mcCurVarible.Max_ic > (mcCurVarible.Max_ia * 2)) || (mcCurVarible.Max_ic > (mcCurVarible.Max_ib * 2)))
                && (mcCurVarible.Max_ic > PhaseLossCurrentValue))
            {
                mcFaultDect.COpencnt++;
            }
            else
            {
                if (mcFaultDect.COpencnt > 0)
                {
                    mcFaultDect.COpencnt --;
                }
            }
            
            mcCurVarible.Max_ia = 0;
            mcCurVarible.Max_ib = 0;
            mcCurVarible.Max_ic = 0;
            SetBit(FOC_CR2, ICLR);
            
            if ((mcFaultDect.AOpencnt > 1) || (mcFaultDect.BOpencnt > 1) || (mcFaultDect.COpencnt > 1))
            {
                mcProtectTime.LossPHTimes++;
                mcFaultSource = FaultLossPhase;
                mcState = mcFault;
            }
        }
    }
    
    #if (!StartONOFF_Enable)
    {
        /*******缺相保护恢复*********/
        if ((mcFaultSource == FaultLossPhase) && (mcState == mcFault)) //&& (mcProtectTime.LossPHTimes <= PhaseLossRestartTimes)) //可重启5次
        {
            mcFaultDect.mcLossPHRecCount++;
            
            if (mcFaultDect.mcLossPHRecCount >= PhaseLossRecoverTime)
            {
                mcFaultDect.AOpencnt = 0;
                mcFaultDect.BOpencnt = 0;
                mcFaultDect.COpencnt = 0;
//                mcState           = mcReady;
                mcFaultSource     = FaultNoSource;
            }
        }
        else
        {
            mcFaultDect.mcLossPHRecCount = 0;
        }
    }
    #endif
}

/*  -------------------------------------------------------------------------------------------------
    Function Name  : Fault_Detection
    Description    : 保护函数，因保护的时间响应不会很高，采用分段处理，每5个定时器中断执行一次对应的保护
                     常见保护有过欠压、过温、堵转、启动、缺相等保护，调试时，可根据需求，一个个的调试加入。
    Date           : 2020-04-10
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */
void Fault_Detection(void)
{
  
        if (OverSoftCurrentEnable) //过流保护恢复使能
        {
//						Fault_OverCurrentRecover();
            Fault_Overcurrent();
        }
    
   
        if (VoltageProtectEnable == 1) //过压保护使能
        {
            Fault_OverUnderVoltage();
        }
    
 
  
        if (StallProtectEnable == 1) //堵转保护使能
        {
            Fault_Stall();
        }
  
        if (PhaseLossProtectEnable == 1) //缺相保护使能
        {
            Fault_phaseloss();
        }
    
}