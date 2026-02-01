/*  -------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen ---------------------------*/
/*  File Name      : AddFunction.c
/*  Author         : Fortiortech  Appliction Team
/*  Version        : V1.0
/*  Date           : 2020-08-21
/*  Description    : This file contains XX-XX-XX function used for Motor Control.
/*  ----------------------------------------------------------------------------------------------*/
/*                                     All Rights Reserved
/*  ----------------------------------------------------------------------------------------------*/

#include "MyProject.h"
#include "math.h"

uint8 data isCtrlPowerOn = false;


FaultStateType             mcFaultSource;

FaultVarible       idata   mcFaultDect;
CurrentVarible     mcCurVarible;
ProtectVarible     xdata   mcProtectTime;
PWMINPUTCAL    xdata mcPwmInput;

MCRAMP             idata   mcSpeedRamp;
MCRAMP             idata   mcPluseramp;
MCRAMP             idata   mcSpeedRampLim;

FOCCTRL            xdata   mcFocCtrl;
UQ_Posi						 xdata   UqPo;

SPlanTypeDef   xdata mcSP;

_PID  pid_Pose;               //

extern float MinAngleLim;
extern float MaxAngleLim;


/*  -------------------------------------------------------------------------------------------------
    Function Name  : Abs_F32
    Description    : 对变量取32位的绝对值
    Date           : 2020-04-10
    Parameter      : value: [输入/出]
    ------------------------------------------------------------------------------------------------- */
uint32 Abs_F32(int32 value)
{
    if (value < 0)
    {
        return (-value);
    }
    else
    {
        return (value);
    }
}


/*  -------------------------------------------------------------------------------------------------
    Function Name  : HW_One_PI
    Description    : PI控制
    Date           : 2020-04-10
    Parameter      : Xn1: [输入/出]
    ------------------------------------------------------------------------------------------------- */
int16 HW_PI_0(int16 Xn1)
{
    PI0_EK = Xn1;          //填入EK
    SetBit(PI_CR, PI0STA); // Start PI
    _nop_();
    _nop_();
    _nop_();
    _nop_();
    return PI0_UKH;
}

int16 HW_PI_1(int16 Xn1)
{
    PI1_EK = Xn1;          //填入EK
    SetBit(PI_CR, PI1STA); // Start PI
    _nop_();
    _nop_();
    _nop_();
    _nop_();
    return PI1_UKH;
}

int16 HW_PI_2(int16 Xn1)
{
    PI2_EK = Xn1;          //填入EK
    SetBit(PI_CR, PI2STA); // Start PI
    _nop_();
    _nop_();
    _nop_();
    _nop_();
    return PI2_UKH;
}
int16 HW_PI_3(int16 Xn1)
{
    PI3_EK = Xn1;          //填入EK
    SetBit(PI_CR, PI3STA); // Start PI
    _nop_();
    _nop_();
    _nop_();
    _nop_();
    return PI3_UKH;
}


float PID_pose(_PID * PID, float err)
{
    //误差
    PID->err = err;
    //    if (PID->err > 4000) PID->err = 4000;
    //    if (PID->err < -4000) PID->err = -4000;
    //    if (PID->err < 30 && PID->err > -30)
    //    {
    //        PID->err  = 0;
    //        PID->integral = 0;
    //    }
    //    if (PID->err < 200){
    //误差积分
    PID->integral += PID->err;
    //  }
    // 积分限幅
    PID->integral = (PID->integral > I_Value(0.05)) ?  I_Value(0.05) : PID->integral;
    PID->integral = (PID->integral < -I_Value(0.05)) ? -I_Value(0.05) : PID->integral;
    PID->voltage    = PID->Kp * PID->err
        + PID->Ki * PID->integral;
    //                    + PID->Kd * (PID->err - PID->err_last);
    PID->voltage = (PID->voltage > I_Value(0.6)) ?  I_Value(0.6) : PID->voltage;
    PID->voltage = (PID->voltage < -I_Value(0.6)) ? -I_Value(0.6) : PID->voltage;
    //上一次的误差
    PID->err_last = PID->err;
    return PID->voltage ;
}
//用于初始化PID值
void PID_init(_PID * PID, float Kp, float Ki, float Kd)
{
    PID->SetVal = 45;
    PID->ActualVal = 0;
    PID->err = 0;
    PID->err_last = 0;
    PID->integral = 0;
    PID->Kp = Kp;
    PID->Ki = Ki;
    PID->Kd = Kd;
}

///
/*  -------------------------------------------------------------------------------------------------
    Function Name  : Speed_response
    Description    : 速度响应函数，可根据需求加入控制环，如恒转矩控制、恒转速控制、恒功率控制
    Date           : 2020-04-10
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */
int32 speedRef;

int32 speedErr;
uint8 pos_loopCnt = 0;
extern float spd;
int32 PosErr;

extern uint8 singal;
extern uint8 PosErrSET;
int16 t1 = 0;


void Speed_response(void)
{
    //    int32 errPre;
    int32 data IqSum;
    
    if ((mcState == mcRun))
    {
        switch (mcFocCtrl.CtrlMode)
        {
            case 0:
            {
                mcFocCtrl.CtrlMode  = 1;
                FOC_DQKP            = DQKP;
                FOC_DQKI            = DQKI;
            }
            break;
            
            case 1:
            {							 
                if (pos_loopCnt < 2)
                {
                    pos_loopCnt ++;
                }
                else
                {      
									PosErr =  mcSP.PulsesNum - mcQEP.CntrSumReal;        
									if (PosErr > 30000)
									{
											PosErr =  30000;
									}
									if (PosErr < -30000)
									{
											PosErr = -30000;
									}        
									speedRef = (PosErr);//(PosErr<<2)+(PosErr>>1);
                  pos_loopCnt = 0;
                }
								mcFocCtrl.PosiErr = PosErr;
                mc_ramp(&mcSpeedRampLim);        //10
                LPF_MDU(mcSpeedRampLim.ActualValue, 5, mcSpeedRampLim.ActualValueFlt, mcSpeedRampLim.ActualValueFlt_LSB);
                
                if (speedRef > mcSpeedRampLim.ActualValueFlt)
                {
                    speedRef =  mcSpeedRampLim.ActualValueFlt ;
                }
                
                if (speedRef < -mcSpeedRampLim.ActualValueFlt)
                {
                    speedRef = - mcSpeedRampLim.ActualValueFlt ;
                }
                #if (Speed_Method == T_Method)
                {
                    speedErr = (int32)speedRef - mcFocCtrl.SpeedFlt;
                }
                #elif (Speed_Method == M_Method)
                {
                    speedErr = (int32)speedRef - mcQEP.SpeedMFlt;
                }
                #endif
                if (speedErr >  30000)
                {
                    speedErr =  30000;
                }
                
                if (speedErr < -30000)
                {
                    speedErr = -30000;
                }
								if((speedErr >= -70)&&(speedErr <= 70))
								{
									mcQEP.timecnt++;
									if(mcQEP.timecnt >= 3500)
									{
										mcQEP.timecnt = 0;
										speedErr = 0;
									}
								}
								else
								{
									if(mcQEP.timecnt > 0)
									{
										mcQEP.timecnt--;
									}
									
								}
                mcFocCtrl.mcIqref =  HW_PI_2(speedErr);
								if(mcFocCtrl.ThetaIQ_SOURCE == 0)
								{
									FOC_IQREF = -mcFocCtrl.mcIqref;
								}
								else
								{
									
								}
            }
            break;
        }
    }
    else
    {
        //        if (Uart.Go_State == 2) //错误 没有执行
        //        {
        //            if (Uart.Go_Time > 3000) //3s 没有执行
        //            {
        //                Uart.Go_State = 0;
        //                Uart.EnableTimeCnt  = 0 ;//禁止计时器
        //                Uart.Go_Time = 0;
        //                Send_Fail();//执行失败
        //            }
        //        }
    }
}

void PWMInputCapture(void)
{
    uint16 MotorSpeedVSP;
    
    if (mcPwmInput.PwmUpdateFlag == 1) // 有新的duty更新
    {
        if ((Abs_F32(mcPwmInput.TimeDR - mcPwmInput.PwmCompareOld) < 0xFF) // 误差在1个Byte之间再处理
            && (Abs_F32(mcPwmInput.PwmArrOld - mcPwmInput.TimeARR) < 0xFF))      // 误差在1个Byte之间再处理
        {
            mcPwmInput.PwmCompare = (mcPwmInput.TimeDR >> 1);// 对其乘以32768
            mcPwmInput.PwmArr     = mcPwmInput.TimeARR;
            mcPwmInput.PwmDuty = _Q15((float)mcPwmInput.TimeDR/mcPwmInput.TimeARR);
//            DivQ_L_MDU(mcPwmInput.PwmCompare, 0x0000, mcPwmInput.PwmArr, mcPwmInput.PwmDuty);
//            ClrBit(TIM3_CR1, T3IPE);          //输入Timer PWM周期检测中断使能 0-->Disable  1-->Enable
//            ClrBit(TIM3_CR1, T3IFE);          //计数器上溢中断使能 0-->Disable  1-->Enable
        }
        
        mcPwmInput.PwmUpdateFlag = 0;
        mcPwmInput.PwmCompareOld = mcPwmInput.TimeDR;//将此次比较值赋值给上次比较值
        mcPwmInput.PwmArrOld     = mcPwmInput.TimeARR;//将此次周期值赋值给上次周期值
    }
}

void SpeedPlanMs(void)
{
    //    float PulsesErr;
    //    float temp;
    //
    //    PulsesErr = mcSP.TargetPulsesNum - mcSP.PulsesNum;
    //
    //    if (PulsesErr >= mcSP.ACCPulsesNum)
    //    {
    //        if (mcSP.Speed < (mcSP.TargetSpeed-mcSP.Acc))
    //        {
    //            mcSP.Speed += mcSP.Acc;
    //            mcSP.AccReal = mcSP.Acc;
    //        }
    //    }
    //    else  if (PulsesErr <= -mcSP.ACCPulsesNum)
    //    {
    //        if (mcSP.Speed > (-mcSP.TargetSpeed+mcSP.Acc))
    //        {
    //            mcSP.Speed  -= mcSP.Acc;
    //            mcSP.AccReal = -mcSP.Acc;
    //        }
    //    }
    //    else if (PulsesErr < mcSP.ACCPulsesNum && PulsesErr>1)
    //    {
    //        if (mcSP.Speed > mcSP.Acc)
    //        {
    //            mcSP.Speed  -= mcSP.Acc;
    //            mcSP.AccReal = -mcSP.Acc;
    //        }
    //    }
    //    else if(PulsesErr >= -mcSP.ACCPulsesNum && PulsesErr < -1)
    //    {
    //        if (mcSP.Speed < (-mcSP.Acc))
    //        {
    //            mcSP.Speed += mcSP.Acc;
    //            mcSP.AccReal = mcSP.Acc;
    //        }
    //        else
    //        {
    //            mcSP.AccReal = 0;
    //        }
    //    }
    //    else
    //    {
    //        mcSP.AccReal = 0;
    //        mcSP.Speed = 0;
    //    }
    //
    //    mcSP.PulsesNum = mcSP.PulsesNum + mcSP.Speed;
}

void mc_ramp(MCRAMP * hSpeedramp)
{
    if (--hSpeedramp->DelayCount < 0)
    {
        hSpeedramp->DelayCount = hSpeedramp->DelayPeriod;
        
        if (hSpeedramp->ActualValue < hSpeedramp->TargetValue)
        {
            if (hSpeedramp->ActualValue + hSpeedramp->IncValue < hSpeedramp->TargetValue)
            {
                hSpeedramp->ActualValue += hSpeedramp->IncValue;
            }
            else
            {
                hSpeedramp->ActualValue = hSpeedramp->TargetValue;
            }
        }
        else
        {
            if (hSpeedramp->ActualValue - hSpeedramp->DecValue > hSpeedramp->TargetValue)
            {
                hSpeedramp->ActualValue -= hSpeedramp->DecValue;
            }
            else
            {
                hSpeedramp->ActualValue = hSpeedramp->TargetValue;
            }
        }
    }
}
