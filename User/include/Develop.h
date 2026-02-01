/*  -------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen ---------------------------*/
/*  File Name      : Develop.h
/*  Author         : Fortiortech  Appliction Team
/*  Version        : V1.0
/*  Date           : 2020-08-31
/*  Description    : This file contains Advanced Applications parameter used for Motor Control.
/*  ----------------------------------------------------------------------------------------------*/
/*                                     All Rights Reserved
/*  ----------------------------------------------------------------------------------------------*/

/*  Define to prevent recursive inclusion --------------------------------------------------------*/
#ifndef __DEVELOP_H_
#define __DEVELOP_H_

/*CPU Parameter*/
#define MCU_CLOCK                      (24.0)                                 // (MHz) 主频

/*single resistor sample Parameter*/
#define MIN_WIND_TIME                  (PWM_DEADTIME + 1.0)                   // (us) 单电阻最小采样窗口，建议值死区时间+0.9us

/*double resistor sample Parameter*/
#define DLL_TIME                        (3.2)                                 // 双电阻最小脉宽设置(us),建议值为死区时间值+0.2us以上
/*three resistor overmodule Parameter*/
#define OVERMOD_TIME                    (0.0)                                 // 三电阻过调制时间(us)，建议值2.0
/*deadtime compensation*/
#define DT_TIME                         (0.0)                                 // 死区补偿时间(us)，适用于双电阻和三电阻，建议值是1/2死区时间
/*min pulse*/
#define GLI_TIME                        (0.0)                                 // 桥臂窄脉宽消除(us),建议值0.5

#define OverModulation                  (0)                                   // 0-禁止过调制，1-使能过调制




/*Current Calib:enable or disable*/
#define Disable                         (0)
#define Enable                          (1)
#define CalibENDIS                      (Enable)

/*SVPWM mode*/
#define SVPWM_5_Segment                 (0)                                    // 五段式SVPWM
#define SVPWM_7_Segment                 (1)                                    // 七段式SVPWM
#define SVPMW_Mode                      (SVPWM_7_Segment)

/*double resistor sample mode*/
#define DouRes_1_Cycle                  (0)                                    // 1 周期采样完 ia, ib
#define DouRes_2_Cycle                  (1)                                    // 交替采用ia, ib, 2周期采样完成
#define DouRes_Sample_Mode              (DouRes_1_Cycle)

/*模式选择设置值----------------------------------------------------------------*/
#define IPMtest                         (0)                                    // IPM测试或者MOS测试，MCU输出固定占空比
#define NormalRun                       (1)                                    // 正常按电机状态机运行


#define CW                              (0)                                     //正转
#define CCW                             (1)                                     //反转

/*电流采样模式*/
#define Single_Resistor                 (0)                                    // 单电阻电流采样模式
#define Double_Resistor                 (1)                                    // 双电阻电流采样模式
#define Three_Resistor                  (2)                                    // 三电阻电流采样模式


/*硬件过流保护比较值来源*/
#define Compare_DAC                     (0)                                   // DAC设置硬件过流值
#define Compare_Hardware                (1)                                   // 硬件设置硬件过流值

#define Long_Inject                     (0)                                     // 脉冲注入时间长于2ms,若时间长于4ms，则要修改定时器分频
#define Short_Inject                    (1)                                     // 脉冲注入时间低于2ms

#define UARTMODE                        (0x01)          ///< 串口调速
#define NONEMODE                        (0xA0)          ///< 直接给定值，不调速

#endif

