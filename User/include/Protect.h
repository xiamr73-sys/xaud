/*  -------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen ---------------------------*/
/*  File Name      : Protect.h
/*  Author         : Fortiortech  Appliction Team
/*  Version        : V1.0
/*  Date           : 2020-08-18
/*  Description    : 主要用于电机运行保护条件参数设置.
/*  ----------------------------------------------------------------------------------------------*/
/*                                     All Rights Reserved
/*  ----------------------------------------------------------------------------------------------*/

/*  Define to prevent recursive inclusion --------------------------------------------------------*/
#ifndef __PROTECT_H_
#define __PROTECT_H_

 /*硬件过流保护比较值来源*/
 #define Compare_Mode                   (Compare_DAC)                      		// 硬件过流值的来源

 #define OverHardcurrentValue           (1.2)  //1.25                              	// (A) DAC模式下的硬件过流值

 /*软件过流保护*/
 #define OverSoftCurrentValue           I_Value(0.35)                           	// (A) 软件过流值
 
 #define OverSoftCurrentEnable           (1)                                     // 过流保护使能位, 0，不使能；1，使能

 /*过流恢复*/
 #define CurrentRecoverEnable           (0)                                     // 过流保护使能位, 0，不使能；1，使能
 #define OverCurrentRecoverTime         (1000)                                   // (ms) 过流保护恢复时间

 /*过欠压保护*/
 #define VoltageProtectEnable           (1)                                     // 电压保护，0,不使能；1，使能
 #define Over_Protect_Voltage           (16.0)                                  // (V) 直流电压过压保护值
 #define Over_Recover_Vlotage           (15.5)                                  // (V) 直流电压过压保护恢复值
 #define Under_Protect_Voltage          (6.0)                                 	// (V) 直流电压欠压保护值
 #define Under_Recover_Vlotage          (6.5)                                  // (V) 直流电压欠压保护恢复值

 /*启动保护*/
 #define StartProtectEnable             (1)                                     // 启动保护，0,不使能；1，使能
 #define StartProtectRestartTimes       (255)                                     // 启动保护重启次数，单位：次

 /*堵转保护*/
 #define StallProtectEnable             (0)                                     // 堵转保护，0,不使能；1，使能
 #define MOTOR_SPEED_STAL_MAX_RPM       (50.0)                                // (RPM) 堵转保护最大转速
 #define MOTOR_SPEED_STAL_MIN_RPM       (1.0)                                 // (RPM) 堵转保护最小转速
 #define StallRecoverTime               (1000)                                  // (ms) 启动运行时间
 #define StallProtectRestartTimes       (255)                                     // 堵转保护重启次数，单位：次

 /*缺相保护*/
 #define PhaseLossProtectEnable         (0)                                     // 缺相保护，0,不使能；1，使能
 #define PhaseLossCurrentValue          I_Value(0.5)                            // (A)  缺相电流值
 #define PhaseLossRecoverTime           (600)                                   // (ms) 缺相保护时间
 #define PhaseLossRestartTimes       	(255)                                     // 缺相保护重启次数，单位：次


#endif

