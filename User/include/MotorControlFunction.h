/* --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : MotorControlFunction.h
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-11
    Description    : This file contains motor contorl parameter used for Motor Control.
----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
------------------------------------------------------------------------------------------------- */
/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MOTORCONTROLFUNCTION_H_
#define __MOTORCONTROLFUNCTION_H_
#include "PosCheck.h"
#include "FU68xx_4.h"
#include "Customer.h"
#include "Parameter.h"
#include "AddFunction.h"

typedef struct
{
	uint16 	PowerUpTimeCount;		 
	uint16	mcRunStateCount;
	uint16  ReciveDelayCount;
	uint8   ReciveDelayFlage;
}Timecnt;



/* Define to prevent recursive inclusion -------------------------------------*/
typedef struct
{
  int16   IuOffset;       //Iu的偏置电压
  int32   IuOffsetSum;    //Iu的偏置电压总和
  int16   IvOffset;       //Iv的偏置电压
  int32   IvOffsetSum;    //Iv的偏置电压总和
  int16   Iw_busOffset;   //Iw或Ibus的偏置电压
  int32   Iw_busOffsetSum;//Iw或Ibus的偏置电压总和
  int16   OffsetCount;    //偏置电压采集计数
  int8    OffsetFlag;     //偏置电压结束标志位
}CurrentOffset;

extern Timecnt		 Time;

extern CurrentOffset xdata mcCurOffset;
extern FaultVarible  idata mcFaultDect;


extern void VariablesPreInit(void);
extern void GetCurrentOffset(void);
extern void Motor_Ready (void);
extern void Motor_Init (void);

extern void FOC_Init(void);
extern void Motor_Charge(void);
extern void MC_Stop(void);
extern void Motor_Open(void);
extern void Motor_Align(void);
extern void MotorcontrolInit(void);
extern void BEMFTailWindDealwith(void);
extern void Motor_TailWind(void);
extern void Motor_Stop(void);


#endif