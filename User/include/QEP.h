#ifndef __QEP_H_
#define __QEP_H_

#include <FU68xx_4_Type.h>

//#define QEP_TIM2_Fre                             (3000000.0)  //  (12000000.0)                               // TIM2计数频率12MHz

//#define PlusePerCircle                          (uint16)(8192*4)                   
//#define TempHallThetaBase						(uint32)((uint32)65536*(QEP_TIM2_Fre*Pole_Pairs/(4096*SAMP_FREQ)))
//#define QEPSpeedBase						    (uint32)((float)60.0*QEP_TIM2_Fre/PlusePerCircle/(float)MOTOR_SPEED_BASE*32767)
//#define QEPPluseMinTime                         (uint32)((float)60.0*QEP_TIM2_Fre/PlusePerCircle/(float)MOTOR_SPEED_BASE)

//#define ANGLE_PER_PLASE                         (float)(65536/PlusePerCircle)
//#define ETHETA_PER_PLASE                        (float)(65536*Pole_Pairs/PlusePerCircle)

 #define TIM2_Fre                               (3000000)//(12000000)//(187500.0)                               // TIM2计数频率12MHz

#define PlusePerCircle                          (16384*4.0)//(256*8*4)
#define TempHallThetaBase				            		(uint32)(65536*(TIM2_Fre*Pole_Pairs/(4096*SAMP_FREQ)))
#define QEPSpeedBase					                	(uint32)(32767*((60*TIM2_Fre)/(PlusePerCircle*MOTOR_SPEED_BASE)))
#define QEPPluseMinTime                         (uint32)((60*TIM2_Fre)/(PlusePerCircle*MOTOR_SPEED_BASE))

#define ANGLE_PER_PLASE                         (float)(65536.0/PlusePerCircle)
#define ETHETA_PER_PLASE                        (float)(65536.0/PlusePerCircle*Pole_Pairs)

/* Exported types ------------------------------------------------------------*/
typedef struct
{
    uint16  Cntr;                                   //  Timer2 计数值
    uint16  CntrOld;                                //  上一个载波 Timer2 计数值
	
    uint16  CntrM;                                //  上一个载波 Timer2 计数值
   	uint16  CntrOldM;                                //  上一个载波 Timer2 计数值

    int16   CntrErr;                                //  两个载波之间 CNTR的差值

    uint8   M_CNT;                                //  两个载波之间 CNTR的差值

    int16   Cycle;                                  //  
    int32   CntrSum;                                //  累计脉冲数量（加上偏置角）
    int32   CntrSumOld;                                //  累计脉冲数量（加上偏置角）

    int32   CntrSumReal;                             //  真实累计脉冲数量
	
	  int32   CntrSum_ZeroTemp;
	  

    int32   CntrNumZ;                                //  Z

    uint16  PeriodTime;                             //  周期
    uint8   OverFlowFlag;                           //  周期溢出标记


    uint16  Theta;                                  //  角度
    uint16  SpeedCalBaseH;                          //  速度计算基准高16位
    uint16  SpeedCalBaseL;                          //  速度计算基准低16位
    uint16  AbsSpeed;                               //  速度绝对值
    int16   Speed;                                  //  速度
    int32   SpeedSum;                               // 速度和
    int16   SpeedAvg;

    uint8   Dir;                                    //  方向
    uint8   DirOld;                                 //  上一个载波转动方向
    uint8   DirTemp;                                    //  方向

    int16   SpeedMFlt;
    int16 	SpeedMFlt_LSB;

    int32   PosiErr;
		
		
		int16 PosDiffArray[16];
		int16 PosDiff;
	  int16 PosDiffReal;

		int32 PosDiffSum;
		int32 PosDiffSumTemp;
		uint8 ArrayPointer;
		int16 SpeedM;
		int16 SpeedMOld;
		
		uint8  ZSaveFlag;
		uint16 ZCNTR;
		
		int32 ZeroCntr;
        int32 ZeroNewCntr;
        
        int16 AngleFlt;
        int32 ZeroCntrOld;
				
			uint16 g1msflg;
			
			uint16 timecnt;

}QEPTypedef;

extern QEPTypedef xdata mcQEP;
extern void EXTI_Init(void);
#ednif


