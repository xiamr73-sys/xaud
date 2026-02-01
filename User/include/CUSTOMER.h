/* --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : Customer.h
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-10
    Description    : This file contains customer parameter used for Motor Control.
----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
------------------------------------------------------------------------------------------------- */
/* Define to prevent recursive inclusion --------------------------------------------------------*/
#ifndef __CUSTOMER_H_
#define __CUSTOMER_H_

#define I_ValueX(Curr_Value)            ((Curr_Value) * (HW_RSHUNT) * (HW_AMPGAIN) / (HW_ADC_REF))
#define I_Value(Curr_Value)             _Q15(I_ValueX(Curr_Value))
#define S_Value(speed)                  _Q15(speed/MOTOR_SPEED_BASE)
#define A_Value(angle)                  _Q15(angle/180.0)
#define P_Value(angle)                  (int32)(angle / 360.0 * PlusePerCircle)
#define C_Value(sum)                    (int32)(sum * 8192 / PlusePerCircle)            //sun*32767
// #define TA_Value(angle)                  (int32)(16 * angle * 360.0 / PlusePerCircle)
// #define TS_Value(speed)                  (speed * MOTOR_SPEED_BASE /128)


#define M_Method    (0)
#define T_Method    (1)


#define Speed_Method    M_Method

/*芯片参数值-------------------------------------------------------------------*/
/*PWM Parameter*/
#define PWM_FREQUENCY                  (24.0)                                  // (kHz) 载波频率
// 20
/*deadtime Parameter*/
#define PWM_DEADTIME                   (0.8)                                   // (us) 死区时间

/*电机参数值-------------------------------------------------------------------*/

#define Pole_Pairs                     (11.0)                                   // 极对数

#define MOTOR_SPEED_BASE               (120.0)//(60.0)           //200                     // (RPM) 速度基准

/*硬件板子参数设置值------------------------------------------------------------*/

/*电机电流采样相关硬件参数*/

#define AMP0_VHALF                     (1)                                     // AMP0是否存在Vhalf偏置电压 1有偏置电压  0没有接偏置电压
#define HW_RSHUNT                      (0.20)                                  // (Ω)  采样电阻
#define HW_ADC_REF                     (5.0)                                   // (V)  ADC参考电压
#define HW_AMPGAIN                     (10.0)                                   // 运放放大倍数
// AMP0放大倍数：AMP2x：2倍   AMP4x：4倍    AMP8x：8倍 AMP16x：16倍  AMP32x：32倍
/*电机驱动母线电压采样相关硬件参数*/
#define VOLTAGE_MODE                   (INTERNAL)                              // 母线电压选择使用分压通道，INTERNAL内部分压  EXTERNAL外部分压
#define RV1                            (12.0)                                  // (kΩ) 母线电压分压电阻1
#define RV2                            (0.0)                                   // (kΩ) 母线电压分压电阻2
#define RV3                            (1.0)                                   // (kΩ) 母线电压分压电阻3
#define RV                             (6.5)//((RV1 + RV2 + RV3) / RV3)              // 选择外部分压时分压系数
/* ---RV分压比例系数  Ratio_12 ：母线分压系数为1:12，   Ratio_6_5 ：母线分压系数为1:6.5-----    ((RV1 + RV2 + RV3) / RV3)  */
#define VOLTAGE_SCALE                  (Ratio_6_5)


/*时间设置值-------------------------------------------------------------------*/
#define Calib_Time                     (1000)                                  // 校正次数，固定1000次，单位:次
#define Charge_Time                    (20)                                    // (ms) 预充电时间，单位：ms

/*启动参数参数值----------------------------------------------------------------*/
#define AlignTestMode                  (0)                                     // 预定位测试模式
#define Align_Angle                    (0.0)                                 // (°) 预定位角度

/*逆风判断时的估算算法设置值-----------------------------------------------------*/
#define ATO_BW_Wind                     (10)                                    // 逆风判断观测器带宽的滤波值，经典值为8.0-100.0
#define SPD_BW_Wind                     (10.0)                                  // 逆风判断速度带宽的滤波值，经典值为5.0-40.0

/***预定位的Kp、Ki****/
#define DQKP_Alignment                 _Q12(1.0)                               // 预定位的KP
#define DQKI_Alignment                 _Q15(0.01)                              // 预定位的KI
#define ID_Align_CURRENT               I_Value(0.2)                            // (A) D轴定位电流
#define IQ_Align_CURRENT               I_Value(0.0)                            // (A) Q轴定位电流

#define Align_Time                      (2000)                           // (A) Q轴定位电流



/***启动电流****/
#define ID_Start_CURRENT               I_Value(0.0)                            // (A) D轴启动电流
#define IQ_Start_CURRENT               I_Value(0.0)                            // (A) Q轴启动电流

/* motor run speed value */

#define MOTOR_SPEED_MIN_RPM            (200.0)                                 // (RPM) 运行最小转速
#define MOTOR_SPEED_MAX_RPM            (2000.0)                                // (RPM) 运行最大转速

#if  (Speed_Method == M_Method)
    
    #define DQKP                           _Q12(1.2) //3.25                             // 运行DQ轴KP
    #define DQKI                           _Q15(0.005)//0.02                     // 运行DQ轴KI
    
    #define DQKP1                           _Q12(1.25) //3.25                             // 运行DQ轴KP
    #define DQKI1                           _Q15(0.005)//0.02                     // 运行DQ轴KI
    
    
    /* D轴参数设置 */
    #define DOUTMAX                        _Q15(0.5)                               // D轴最大限幅值，单位：输出占空比
    #define DOUTMIN                        _Q15(-0.5)                              // D轴最小限幅值，单位：输出占空比
    /* Q轴参数设置 */
    #define QOUTMAX                        _Q15(0.95)                               // Q轴最大限幅值，单位：输出占空比
    #define QOUTMIN                        _Q15(-0.95)                              // Q轴最小限幅值，单位：输出占空比
    
    
    #define SKP                            _Q12(2.2)   //1.0                        // 外环KP
    #define SKI                            _Q15(0.001)  //0.02                           // 外环KI
    #define SKD                            _Q15(0.000)
    
    #define SKP1                           _Q12(1.0)   //1.0                         // 外环KP
    #define SKI1                            _Q15(0.002)  //0.002                           // 外环KI
    #define SKD                             _Q15(0.000)
    
#elif  (Speed_Method == T_Method)
    
    
    #define DQKP                           _Q12(0.5) //0.9                             // 运行DQ轴KP
    #define DQKI                           _Q15(0.002)//0.008     0.006                        // 运行DQ轴KI
    /* D轴参数设置 */
    #define DOUTMAX                        _Q15(0.3)                               // D轴最大限幅值，单位：输出占空比
    #define DOUTMIN                        _Q15(-0.3)                              // D轴最小限幅值，单位：输出占空比
    /* Q轴参数设置 */
    #define QOUTMAX                        _Q15(0.92)                               // Q轴最大限幅值，单位：输出占空比
    #define QOUTMIN                        _Q15(-0.92)                              // Q轴最小限幅值，单位：输出占空比
    
    
    #define SKP                            _Q12(1.0)   //1.0                         // 外环KP
    #define SKI                            _Q15(0.01)  //0.01                           // 外环KI
    #define SKD                            _Q15(0.00)
    
    #define SKP1                           _Q12(3.9)   //3.9                         // 外环KP
    #define SKI1                            _Q15(0.0935)  //0.0335                            // 外环KI
    #define SKD                            _Q15(0.000)
    
#endif

// #define SOUTMAX                        I_Value(0.4)                            // (A) 外环最大限幅值
// #define SOUTMIN                        I_Value(-0.4)                            // (A) 外环最小限幅值

#define SOUTMAX                        I_Value(0.445)                            // (A) 外环最大限幅值
#define SOUTMIN                        I_Value(-0.445)                            // (A) 外环最小限幅值
// 外环KI
// #define SKP                            _Q12(7.6)   //5.2                           // 外环KP
// #define SKI                            _Q15(0.003)  //0.003                            // 外环KI
// #define SKD                            _Q15(0.000)

#define PosKP                            _Q12(7.0) //4.5                              // 外环KP
#define PosKI                            _Q15(0.00)                              // 外环KI
#define PosKD                            _Q15(0.00)                              // 外环KI

#define POUTMAX                        S_Value(20.0)                            // (A) 外环最大限幅值
#define POUTMIN                        S_Value(-20.0)                            // (A) 外环最小限幅值


/*NONEMODE   UARTMODE*/
#define REF_MODE                       (UARTMODE)


/*模式选择设置值----------------------------------------------------------------*/
#define IPMState                       (NormalRun)

/*外环使能OUTLoop_Disable ,输出QOUTCURRENT电流值不调速     OUTLoop_Enable 设置速度外环*/
#define OUTLoop_Mode                   (OUTLoop_Enable)


/*电流采样模式 Single_Resistor单电阻采样电流，Double_Resistor双电阻采样电流  Three_Resistor三电阻采样电流*/
#define Shunt_Resistor_Mode            (Double_Resistor)
#define _Q15Limit(A)                    (A>(int32)32767)?32767:((A<(int32)(-32768))?-32768:A)

/*****************************增加*******************************/
#define ABS(num)   ((num)>=0?(num):(-(num)))

#define DefaultMinAngleCode      (0x2FA)

#define DefaultMaxAngleCode      (0x14D9)

#define DefaultMiddleAngleCode   (0xBE9)

#define SpeedLevel               (0X0B)    //0x00 - 0x18  默认0X0B                 

#define OPEN_TEST    (0)



#define STARTPAGEROMADDRESS 0x3E00
//#define LEARNPAGEROMADDRESS 0x3E00 
//#define PosErrSET    (8)


#define UD_Align_Duty_Max              _Q15(0.25)      ///< (A) D轴定位电压最大值

#endif
