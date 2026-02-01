/* --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : AddFunction.h
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-11
    Description    : This file contains all the common data types used for Motor Control.
----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
------------------------------------------------------------------------------------------------- */
/* Define to prevent recursive inclusion -------------------------------------*/

#ifndef __AddFunction_H_
#define __AddFunction_H_

/******************************************************************************/
#include <FU68xx_4_Type.h>
/******************************************************************************/

/* Exported types ------------------------------------------------------------*/
typedef struct
{
    //Current protect
    uint8  OverCurCnt;                                                          // 软件过流计数

    uint16 Abs_ia;                                                              // IA的绝对值
    uint16 Abs_ib;                                                              // IB的绝对值
    uint16 Abs_ic;                                                              // IC的绝对值

    uint16 Max_ia;                                                              // IA的最大值
    uint16 Max_ib;                                                              // IB的最大值
    uint16 Max_ic;                                                              // IC的最大值
}CurrentVarible;

typedef struct
{
    uint16 TimeDR;               // 比较值
    uint16 PwmCompare;
    uint16 TimeARR;              // 周期值
    uint16 PwmArr;               // 计算中的周期值	
    uint16 PwmCompareOld;        // 上一次的比较值
    uint16 PwmArrOld;            // 上一次的周期值

    uint32 PwmDuty;              // PWM占空比，Q15格式
    uint16 PwmSclk;              // PWM频率
    int16  PwmUpdateFlag;        // PWM新的duty更新
}PWMINPUTCAL;

typedef struct
{
    uint8 SecondStartTimes;                                                    // 二次启动保护的次数
    uint8 StallTimes;                                                          // 堵转保护次数
    uint8 LossPHTimes;                                                         // 缺相保护次数
    uint8 CurrentPretectTimes;                                                 // 过流保护次数
    uint8  StartFlag;                                                           // 启动保护的标志位，用于判断哪个方法起作用
    uint8  StallFlag;                                                           // 堵转保护的标志位，用于判断哪个方法起作用
}ProtectVarible;
typedef struct
{
    uint16 segment;                                                             // 分段执行

    //voltage protect
    uint16 OverVoltDetecCnt;                                                    // 过压检测计数
    uint16 UnderVoltDetecCnt;                                                   // 欠压检测计数
    uint16 VoltRecoverCnt;                                                      // 过压恢复计数

    //OVER Current protect recover
    uint16 CurrentRecoverCnt;                                                   // 过流保护恢复计数
		uint8  CurrentFlag;
	
    //stall protect
    uint16 StallDelayCnt;                                                       // 堵转延迟判断计时
    uint16 UnderVoltageDelayCnt;
    uint16 StallDectEs;                                                         // method 1，与ES相关
    uint16 StallDectSpeed;                                                      // method 2，与速度相关
    uint16 StallDectESSpeed;                                                    // method 3，与ES和速度相关
    uint16 StallReCount;                                                        // 堵转保护恢复计数
    uint16 StallSpeedAndEsCnt;

    // uint16 StallRecover;                                                     // 堵转保护恢复时间
    //Loss Phase protect

    uint16 Lphasecnt;                                                           // 缺相保护计时
    uint16 AOpencnt ;                                                           // A缺相计数
    uint16 BOpencnt ;                                                           // B缺相计数
    uint16 COpencnt ;                                                           // C缺相计数
    uint16 mcLossPHRecCount;                                                    // 缺相恢复计数
    //start protect

    uint16 StartESCount;                                                         // 启动保护判断ES的计数
    uint16 StartEsCnt;                                                           // 启动保护判断ES的计时
    uint16 StartDelay;                                                           // 启动保护判断ES的延迟
    uint16 StartFocmode;                                                         // 启动保护判断FOCMODE状态的计时
    uint16 StartSpeedCnt;                                                        // 启动保护判断速度和ES的计时
    uint16 StartSpeedAndEsCnt;
}FaultVarible;

typedef struct
{
    int16   TargetValue;
    int16   ActualValue;
    int16   IncValue;
    int16   DecValue;
    int16   DelayCount;
    int16   DelayPeriod;
   int16    ActualValueFlt;
    int16    ActualValueFlt_LSB;
    int8    FlagONOFF;
}MCRAMP;

typedef enum
{
    FaultNoSource      = 0,                                                     // 无故障
    FaultHardOVCurrent = 1,                                                     // 硬件过流
    FaultSoftOVCurrent = 2,                                                     // 软件过流
    FaultUnderVoltage  = 3,                                                     // 欠压保护
    FaultOverVoltage   = 4,                                                     // 过压保护
    FaultLossPhase     = 5,                                                     // 缺相保护
    FaultStall         = 6,                                                     // 堵转保护
    FaultStart         = 7,                                                     // 启动保护
    FaultOverwind      = 8,                                                     // 顺逆风失败保护
    FaultPFC           = 9,                                                     // PFC
} FaultStateType;

typedef struct
{
//    uint16 ADCDcbus;                                                            // 母线电压
//    uint16 ADCSpeed;                                                            // 模拟速度
    uint16 ADCVref;                                                             // ADC参考
} ADCSample;

typedef struct
{
    uint32 ONOFF_Times;                                                         // 启停次数
    uint16 ON_Count;                                                            // 运行时间计数
    uint16 OFF_Count;                                                           // 停止时间计数
    uint8  ONOFF_Flag;                                                          // 启停测试中启动标志位
} ONVarible;

typedef struct
{
    uint16 mcDcbusFlt;                                                          // 母线电压
    int16  mcDcbusFlt_LSB;                                                      // 当前母线电压滤波后的值
    
    uint16 CtrlMode;                                                            // 控制模式
    
    uint16 CurrentPower;                                                        // 当前功率
    int16  Powerlpf;                                                            // 功率滤波后的值
    int16  Powerlpf_LSB;                                                        // 功率滤波后的值
    
    int16  mcIqref;                                                             // Q轴给定电流

    int16  McuRef;
    int16  mcPosCheckAngle;                                                     // 位置检测的角度
  
    int16  SpeedFlt;                                                            // 当前速度滤波后的值
    int16  SpeedFlt_LSB;                                                        // 当前速度滤波后的值
  
  int16  SpeedFlt2;                                                            // 当前速度滤波后的值

  int16 SpeedRef;
      int16  SpeedFltFlt;                                                            // 当前速度滤波后的值
    int16  SpeedFltFlt_LSB;  
   int16  SpeedRefLim;
    uint16 ChargeStep;                                                          // 预充电的步骤
    uint16 State_Count;                                                         // 电机各个状态的时间计数
    uint16 SoftStart_Count;
    uint8  SoftStart_Flag;
    
    uint8  Lrean_State;
    int16  LreanAngle;
    int16  LreanAngleFlt;
    int16  LreanAngleFlt1;
    int16  LreanAngleFlt1_LSB;
    int16  LreanAngleFlt2;
    int16  LreanAngleFlt2_LSB;
    uint16 LreanTimeCnt;
		
		uint8 UQTurnFlag;//切q轴电流强拖标志位
		uint8 UQLockFlag;
		uint8 ThetaIQ_SOURCE;//电机电角度来源
		uint16 Timedelay;
		
		int32 PosiErr;
}FOCCTRL;



typedef struct
{
    uint16 Read;
    uint16 Sum;
    uint16 RealValue;
}VspInput;

//typedef struct
//{
//    uint8  TargetFR;                  // 设置的目标方向
//    int16  TargetValue;
//    int16  ActualValue;
//    int16  IncValue;
//    int16  DecValue;
//    int16  DelayCount;
//    int16  DelayPeriod;
//    int8   FlagONOFF;
//}MCRAMP;


typedef struct
{
    int16  ACCPulsesNum;                  
    
    float  Acc;
    float  AccReal;
    float  Speed;
    
    float  TargetSpeed; 
    float  TargetSpeed2; 
    
    int32 PulsesNum;
      int32 PulsesNumStop;

    int32 TargetPulsesNum;
    
    uint8 Speedlevel;
	


}SPlanTypeDef;


typedef struct{
    float SetVal;
    float ActualVal;
    float err;
    float err_last;
    float Kp;
    float Ki;
    float Kd;
    float voltage;			
    float integral;
}_PID;

typedef union 
{
    int32  s32;                                                                 // 比较值标幺化的值
    int16  s16[2];
}S32tS16;

typedef struct
{
    int16   Ref;

    int16   Err;
    int16   Err_last;
    int16   Ref_last;
    int16   Fb_last;
    int32   Integral;
    int32   Uk;
    int16   Uk_max;
    int16   Uk_min;
    int32   Ki_max;
    int32   Ki_min;
    uint16  Kp;
    uint16  Ki;
    uint16  Kf;
}PI_Typedef;


typedef struct
{
	uint8 UqPoaiFlag;
	int16 EThetaN;
	int16 ThetaN;
	int16 IQN;
	uint8 UqPosiLockFlag;
	uint8 PosiLockFlag;
}UQ_Posi;

/* Exported variables ---------------------------------------------------------------------------*/

extern FaultVarible   idata mcFaultDect;
extern CurrentVarible  mcCurVarible;
extern ProtectVarible xdata mcProtectTime;
extern ONVarible       ONOFFTest;
extern FaultStateType xdata mcFaultSource;
extern ADCSample       AdcSampleValue;
extern FOCCTRL        xdata mcFocCtrl;
extern MCRAMP         xdata MotorSpeed;

extern SPlanTypeDef   xdata mcSP;
extern PWMINPUTCAL    xdata mcPwmInput;

extern uint8 data isCtrlPowerOn;



extern uint16 FGDelayOutputTimer;


/* Exported functions ---------------------------------------------------------------------------*/
extern void   Fault_OverUnderVoltage(void);
extern void   Fault_Overcurrent(void);
extern void   Fault_OverCurrentRecover(void);
extern void   Fault_Stall(void);
extern void   Fault_phaseloss(void);
extern void   VariablesPreInit(void);
extern void   Fault_Detection(void);
extern void   PWMInputCapture(void);


extern void   SpeedPlanMs(void);
extern void   Speed_response(void);
extern void   mc_ramp(MCRAMP *hSpeedramp);
extern void   VSPSample(void);
extern int16  HW_One_PI(int16 Xn1);
extern void   FaultProcess(void);

extern uint32 Abs_F32(int32 value);
extern MCRAMP             idata   mcSpeedRamp;
extern MCRAMP             idata   mcSpeedRampLim;
extern MCRAMP             idata   mcPluseramp;
extern UQ_Posi             xdata   UqPo;

extern void PostionControlV2(void);
extern void PostionControlV1(void);
extern void SingleSpeedControl(void);
extern void SpeedParInit(void);
extern void TurnMotor(uint32 angle);
extern void mc_ramp(MCRAMP * hSpeedramp);


#endif