/* --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : MotorSpeedFunction.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-10
    Description    : This file contains .C file function used for Motor Control.
----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
------------------------------------------------------------------------------------------------- */
#include <MyProject.h>

CurrentOffset xdata mcCurOffset;
bool OpenFlag;
uint8 Data[4]={0};

/* -------------------------------------------------------------------------------------------------
    Function Name  : FOC_Init
    Description    : mcInit状态下，对FOC的相关寄存器进行配置,先清理寄存器，后配置，最后使能
    Date           : 2020-04-10
    Parameter      : None
------------------------------------------------------------------------------------------------- */
void FOC_Init(void)//MOtor_Init
{
    /*使能FOC*/
    ClrBit(DRV_CR, FOCEN);
    SetBit(DRV_CR, FOCEN);
    SetBit(FOC_CR0, ESCMS);
    ClrBit(FOC_CR0, MERRS1);
    SetBit(FOC_CR0, MERRS0);
    //    FOC_EOMEKLPF    = 0;
    //    FOC_KFG         = MCU_CLOCK * BASE_FREQ * FG_K);
    /*配置FOC寄存器*/
    FOC_CR1         = 0;                                    // 清零 FOC_CR1
    FOC_CR2         = 0;                                    // 清零 FOC_CR2
    FOC_IDREF       = 0;                                    // 清零 Id
    FOC_IQREF       = 0;                                    // 清零 Iq
    //    FOC__THETA      = 0;                                    // 清零 角度
    FOC_RTHEACC     = 0;                                    // 清零 爬坡函数的初始加速度
    FOC__RTHESTEP   = 0;                                    // 清零 爬坡速度
    FOC_RTHECNT     = 0;                                    // 清零 爬坡次数
    FOC_THECOMP     = _Q15(0.0 / 180.0);                    // SMO 估算补偿角
    FOC_THECOR      = 0x04;                                 // 误差角度补偿
    /*电流环参数配置*/
    FOC_DMAX        = DOUTMAX;
    FOC_DMIN        = DOUTMIN;
    FOC_QMAX        = QOUTMAX;
    FOC_QMIN        = QOUTMIN;
    /*位置估算参数配置*/
    //    FOC_FBASE       = OBS_FBASE;
    FOC_EBMFK       = OBS_KLPF;
    FOC_TGLI        = 0x00;
    SetBit(FOC_CR1, SVPWMEN);                               // SVPWM模式
    /**过调制**/
    #if (OverModulation == 1)
    {
        SetBit(FOC_CR1, OVMDL);                             // 过调制
    }
    #endif //end OverModulation
    #if(VOLTAGE_MODE ==INTERNAL)
    {
        SetBit(FOC_CR0, UCSEL);
    }
    #else
    {
        ClrBit(FOC_CR0, UCSEL);
    }
    #endif
		
		SetBit(DRV_CR, DDIR);
    
		
    /*单电阻采样；需要最小采样窗,FOC_TRGDLY为0，七段式SVPWM方式*/
    #if (Shunt_Resistor_Mode == Single_Resistor)
    {
        SetReg(FOC_CR1, CSM0 | CSM1, 0x00);
        FOC_TSMIN  = PWM_TS_LOAD;                           // 最小采样窗口
        FOC_TRGDLY = 0x0F;                                  // 采样时刻在中点，一般考虑开关噪声影响，会设置延迟；
        // 0x0c表示延迟12个clock，提前用反码形式，如0x84表示提前12个clock。
        ClrBit(FOC_CR2, F5SEG);                             // 7段式
        SetReg(CMP_CR1, CMP3MOD0 | CMP3MOD1, 0x00);
    }
    /*双电阻采样，可设置死区补偿值，在下降沿结束前开始采样Ia，配置81*/
    #elif (Shunt_Resistor_Mode == Double_Resistor)          // double resistor sample
    {
        SetReg(FOC_CR1, CSM0 | CSM1, CSM0);
        FOC_TSMIN = PWM_DT_LOAD;                            // 死区补偿值
        FOC_TRGDLY = 0x82;                                  // ADC采样的时刻，采样时刻在计数器零点附近，83为下降沿结束前3个clock采样Ia，与单电阻不同
        // 01为上升沿开始后第一个clock开始采样。根据实际情况调整。
        FOC_TBLO = PWM_DLOWL_TIME;                          //下桥臂最小脉冲，保证采样
        SetReg(CMP_CR1, CMP3MOD0 | CMP3MOD1, 0x00);
        /*五段式或七段式选择*/
        #if (SVPMW_Mode == SVPWM_7_Segment)
        {
            ClrBit(FOC_CR2, F5SEG);                         // 7段式
        }
        #elif (SVPMW_Mode == SVPWM_5_Segment)
        {
            SetBit(FOC_CR2, F5SEG);                         // 5段式
        }
        #endif
        #if (DouRes_Sample_Mode == DouRes_1_Cycle)
        {
            ClrBit(FOC_CR2, DSS);                           // 7段式
        }
        #elif (DouRes_Sample_Mode == DouRes_2_Cycle)
        {
            SetBit(FOC_CR2, DSS);                           // 5段式
        }
        #endif //end DouRes_Sample_Mode
    }
    /*三电阻采样*/
    #elif (Shunt_Resistor_Mode == Three_Resistor)           // signel resistor sample
    {
        SetReg(FOC_CR1, CSM0 | CSM1, CSM0 | CSM1);          // 三电阻
        FOC_TSMIN  = PWM_DT_LOAD;                           // 死区补偿值
        FOC_TRGDLY = 0x06;                                  // ADC采样的时刻，采样时刻在计数器零点附近，83为下降沿结束前3个clock采样Ia，与单电阻不同。
        // 01为上升沿开始后第一个clock开始采样。根据实际情况调整。
        SetReg(CMP_CR1, CMP3MOD0 | CMP3MOD1, CMP3MOD0 | CMP3MOD1);
        FOC_TBLO = PWM_OVERMODULE_TIME;                     // 过调制电流采样处理的TB脉宽
        /*五段式或七段式选择*/
        #if (SVPMW_Mode == SVPWM_7_Segment)
        {
            ClrBit(FOC_CR2, F5SEG);                         // 7段式
        }
        #elif (SVPMW_Mode == SVPWM_5_Segment)
        {
            SetBit(FOC_CR2, F5SEG);                         // 5段式
        }
        #endif //end SVPMW_Mode
        #if (DouRes_Sample_Mode == DouRes_1_Cycle)
        {
            ClrBit(FOC_CR2, DSS);                           // 7段式
        }
        #elif (DouRes_Sample_Mode == DouRes_2_Cycle)
        {
            SetBit(FOC_CR2, DSS);                           // 5段式
        }
        #endif //end DouRes_Sample_Mode
    }
    #endif  //end Shunt_Resistor_Mode
    /* 使能电流基准校正 */
    #if (CalibENDIS == Enable)
    {
        if (mcCurOffset.OffsetFlag == 1)
        {
            #if (Shunt_Resistor_Mode == Single_Resistor)    // 单电阻校正
            {
                /*set ibus current sample offset*/
                SetReg(FOC_CR2, CSOC0 | CSOC1, 0x00);
                FOC_CSO = mcCurOffset.Iw_busOffset;         // 写入Ibus的偏置
            }
            #elif (Shunt_Resistor_Mode == Double_Resistor)  // 双电阻校正
            {
                /*set ia, ib current sample offset*/
                SetReg(FOC_CR2, CSOC0 | CSOC1, CSOC0);
                FOC_CSO  = mcCurOffset.IuOffset;            // 写入IA的偏置
            
                SetReg(FOC_CR2, CSOC0 | CSOC1, CSOC1);
                FOC_CSO  = mcCurOffset.IvOffset;            // 写入IB的偏置
            }
            #elif (Shunt_Resistor_Mode == Three_Resistor)   // 三电阻校正
            {
                /*set ibus current sample offset*/
                SetReg(FOC_CR2, CSOC0 | CSOC1, CSOC0);
                FOC_CSO = mcCurOffset.IuOffset;             // 写入IA的偏置
            
                SetReg(FOC_CR2, CSOC0 | CSOC1, CSOC1);
                FOC_CSO = mcCurOffset.IvOffset;             // 写入IB的偏置
            
                SetReg(FOC_CR2, CSOC0 | CSOC1, 0x00);
                FOC_CSO = mcCurOffset.Iw_busOffset;         // 写入IC的偏置
            }
            #endif  //end Shunt_Resistor_Mode
        }
    }
    #endif  //end CalibENDIS
    /*-------------------------------------------------------------------------------------------------
    DRV_CTL：PWM来源选择
    OCS = 0, DRV_COMR
    OCS = 1, FOC/SVPWM/SPWM
    -------------------------------------------------------------------------------------------------*/
    /*计数器比较值来源FOC*/
    SetBit(DRV_CR, OCS);
}



/* -------------------------------------------------------------------------------------------------
    Function Name  : Motor_Align
    Description    : 预定位函数，当无逆风判断时，采用预定位固定初始位置;当有逆风判断时，采用预定位刹车
    Date           : 2020-04-10
    Parameter      : None
------------------------------------------------------------------------------------------------- */
uint8 AlignFlag = 0;

void Motor_Align(void)
{
    if (McStaSet.SetFlag.AlignSetFlag == 0)
    {
        McStaSet.SetFlag.AlignSetFlag = 1;
        /* -----FOC初始化----- */
        FOC_Init();
        /*配置预定位的电压、KP、KI*/
        FOC_IDREF = ID_Align_CURRENT;
        FOC_IQREF = IQ_Align_CURRENT;               //定义电压
        //        SetBit(FOC_CR2, UDD);
        //        SetBit(FOC_CR2, UQD);
        FOC_DQKP  = DQKP_Alignment;
        FOC_DQKI  = DQKI_Alignment;
        /* 配置预定位角度 */
        FOC__THETA  = Align_Theta;
        /*********PLL或SMO**********/
        #if (EstimateAlgorithm == SMO)
        {
            FOC__ETHETA   = FOC__THETA - 4096;
        }
        #elif (EstimateAlgorithm == PLL)
        {
            FOC__ETHETA   = FOC__THETA;
        }
        #endif //end    EstimateAlgorithm
        /*使能输出*/
        DRV_CMR |= 0x3F;                         // U、V、W相输出
        MOE = 1;
    }
}

/* -------------------------------------------------------------------------------------------------
    Function Name  : Motor_Open
    Description    : 开环启动的参数配置
    Date           : 2020-04-10
    Parameter      : None
------------------------------------------------------------------------------------------------- */

extern uint16 xdata Hall_Angle_Arr[6];
extern uint8  HallStatus;

void Motor_Open(void)
{
    static uint8 OpenRampCycles;
    float PwmDuty;
    float Angle;
    if (McStaSet.SetFlag.StartSetFlag == 0)
    {
        McStaSet.SetFlag.StartSetFlag = 1;
        FOC_Init();
        DRV_CMR |= 0x3F;                         // U、V、W相输出
        MOE = 1;
        if (GP42) 
        {
            mcFocCtrl.LreanAngleFlt = (float)((int32)mcQEP.AngleFlt * 360.0) / 32767;
            PwmDuty = mcPwmInput.PwmDuty / 32767.0;
            Angle = (PwmDuty * 4098 - 1) / 4095 * 360.0 - mcFocCtrl.LreanAngleFlt;//(float)((int32)mcQEP.AngleFlt * 360.0) / 32767;
            TIM2__CNTR = -P_Value(Angle) / Pole_Pairs;
            FOC__THETA = _Q15(Angle /180.0);//ABS(mcFocCtrl.LreanAngleFlt) + ABS(mcFocCtrl.LreanAngleFlt);
        }
        else 
        {
            TIM2__CNTR = 0;
            FOC__THETA = 0;           
        }
        ClrBit(FOC_CR2, UDD);
        ClrBit(FOC_CR2, UQD);
     
        /*启动电流、KP、KI、FOC_EKP、FOC_EKI*/
        FOC_IDREF = ID_Start_CURRENT;                         // D轴启动电流
        FOC_IQREF = IQ_Start_CURRENT;                          // Q轴启动电流
        FOC_DQKP            = DQKP;
        FOC_DQKI            = DQKI;
        //    #elif (Open_Start_Mode == Open_Start)
        FOC_RTHEACC      = 0;      // 爬坡函数的初始加速度
        FOC__RTHESTEP    = 0;      // 0.62 degree acce speed
        FOC_RTHECNT      = 0;       // acce time
        ClrBit(FOC_CR1, EFAE);                                                          // 估算器强制输出
        ClrBit(FOC_CR1, RFAE);                                                          // 禁止强拉
        ClrBit(FOC_CR1, ANGM);
        OpenFlag = 1;
        mcState = mcRun;
    }
}





/* -------------------------------------------------------------------------------------------------
    Function Name  : Motor_Stop
    Description    : inital motor control parameter
    Date           : 2020-04-10
    Parameter      : None
------------------------------------------------------------------------------------------------- */
void Motor_Stop(void)
{
    if ((mcFocCtrl.SpeedFlt < Motor_Min_Speed) || (mcFocCtrl.State_Count == 0))
    {
        #if (StopBrakeFlag == 0)
        {
            mcState = mcReady;
            FOC_CR1 = 0x00;
            ClrBit(DRV_CR, FOCEN);   //关闭FOC
            
            MOE = 0;
            
        }
        #else
        {
            if (mcFocCtrl.SpeedFlt < Motor_Stop_Speed)
            {
                MOE = 0;
                FOC_CR1 = 0x00;
                ClrBit(DRV_CR, FOCEN);
                DRV_DR   = DRV_ARR + 1;
                DRV_CMR  = 0x00;
                DRV_CMR |= 0x015;     // 三相下桥臂通，刹车
                ClrBit(DRV_CR, OCS);  // OCS = 0, DRV_COMR;OCS = 1, FOC/SVPWM/SPWM
                SetBit(DRV_CR, DRVEN);
                MOE = 1;
                mcState  = mcBrake;
                mcFocCtrl.State_Count = StopWaitTime;
            }
        }
        #endif
    }
}

/* -------------------------------------------------------------------------------------------------
    Function Name  : MotorcontrolInit
    Description    : 控制变量初始化清零,包括保护参数的初始化、电机状态初始化
    Date           : 2020-04-10
    Parameter      : None
------------------------------------------------------------------------------------------------- */
int32 debug_Cal;
void MotorcontrolInit(void)
{
    /*****电机状态机时序变量***********/
    McStaSet.SetMode                   = 0;
    /**********电机目标方向*************/
    mcCurOffset.IuOffsetSum            = 16383;
    mcCurOffset.IvOffsetSum            = 16383;
    mcCurOffset.Iw_busOffsetSum        = 16383;
    debug_Cal = QEPSpeedBase;
    mcQEP.SpeedCalBaseH = (QEPSpeedBase >> 16);
    mcQEP.SpeedCalBaseL = (QEPSpeedBase);
    Learn.FilishFlag = 0;
//    mcQEP.ZSaveFlag = 1;
    Data[0] =  *(uint8 code *)(STARTPAGEROMADDRESS); 
    Data[1] += *(uint8 code *)(STARTPAGEROMADDRESS + 1);
    mcQEP.AngleFlt = ((int16)(Data[0] << 8) | (int16)Data[1]);
    Data[0] =  *(uint8 code *)(STARTPAGEROMADDRESS + 2); 
    Data[1] += *(uint8 code *)(STARTPAGEROMADDRESS + 3);
    Data[2] += *(uint8 code *)(STARTPAGEROMADDRESS + 4);
    Data[3] += *(uint8 code *)(STARTPAGEROMADDRESS + 5);
    mcQEP.ZeroNewCntr = ((int32)(Data[0] << 24) | (int32)(Data[1] << 16) | (int32)(Data[2] << 8) | (int32)Data[3]);

}

/* -------------------------------------------------------------------------------------------------
    Function Name  : VariablesPreInit
    Description    : 初始化电机参数
    Date           : 2020-04-10
    Parameter      : None
------------------------------------------------------------------------------------------------- */
void VariablesPreInit(void)
{
    mcFaultSource = 0;
    /* -----保护参数初始化----- */
    memset(&mcFaultDect, 0, sizeof(FaultVarible));                                                                 // FaultVarible变量清零
    /* -----外部控制环参数初始化----- */
    memset(&mcFocCtrl, 0, sizeof(FOCCTRL));
    // mcFocCtrl变量清零
    //    memset(&Uart, 0, sizeof(MCUART));
    memset(&Learn, 0, sizeof(SELFLEARN));
    
    
    /*****电机状态机时序变量***********/
    McStaSet.SetMode                  = 0x01;   //电流校准标志位置1，其它置0
    mcFocCtrl.State_Count = 0;

}

/* -------------------------------------------------------------------------------------------------
    Function Name  : GetCurrentOffset
    Description    : 上电时，先对硬件电路的电流进行采集，写入对应的校准寄存器中。
                     调试时，需观察mcCurOffset结构体中对应变量是否在范围内。采集结束后，OffsetFlag置1。
    Date           : 2020-04-10
    Parameter      : None
------------------------------------------------------------------------------------------------- */
void GetCurrentOffset(void)
{
    if (!mcCurOffset.OffsetFlag)
    {
        SetBit(ADC_CR, ADCBSY);             // 使能ADC
        
        while (ReadBit(ADC_CR, ADCBSY));
        
        #if (Shunt_Resistor_Mode == Single_Resistor)                   //单电阻模式
        {
            mcCurOffset.Iw_busOffsetSum += ((ADC4_DR & 0x7ff8));
            mcCurOffset.Iw_busOffset     = mcCurOffset.Iw_busOffsetSum >> 4;
            mcCurOffset.Iw_busOffsetSum -= mcCurOffset.Iw_busOffset;
        }
        #elif (Shunt_Resistor_Mode == Double_Resistor)                 //双电阻模式
        {
            mcCurOffset.IuOffsetSum     += ((ADC0_DR & 0x7ff8));
            mcCurOffset.IuOffset         = mcCurOffset.IuOffsetSum >> 4;
            mcCurOffset.IuOffsetSum     -= mcCurOffset.IuOffset;
            mcCurOffset.IvOffsetSum     += ((ADC1_DR & 0x7ff8));
            mcCurOffset.IvOffset         = mcCurOffset.IvOffsetSum >> 4;
            mcCurOffset.IvOffsetSum     -= mcCurOffset.IvOffset;
        }
        #elif (Shunt_Resistor_Mode == Three_Resistor)                 //三电阻模式
        {
            mcCurOffset.IuOffsetSum     += ((ADC0_DR & 0x7ff8));
            mcCurOffset.IuOffset         = mcCurOffset.IuOffsetSum >> 4;
            mcCurOffset.IuOffsetSum     -= mcCurOffset.IuOffset;
            mcCurOffset.IvOffsetSum     += ((ADC1_DR & 0x7ff8));
            mcCurOffset.IvOffset         = mcCurOffset.IvOffsetSum >> 4;
            mcCurOffset.IvOffsetSum     -= mcCurOffset.IvOffset;
            mcCurOffset.Iw_busOffsetSum += ((ADC4_DR & 0x7ff8));
            mcCurOffset.Iw_busOffset     = mcCurOffset.Iw_busOffsetSum >> 4;
            mcCurOffset.Iw_busOffsetSum -= mcCurOffset.Iw_busOffset;
        }
        #endif
        mcCurOffset.OffsetCount++;
        
        if (mcCurOffset.OffsetCount > Calib_Time)
        {
            mcCurOffset.OffsetFlag = 1;
        }
    }
}

/* -------------------------------------------------------------------------------------------------
    Function Name  : Motor_Ready
    Description    : 上电时，关闭输出，先对硬件电路的电流进行采集，在FOC_Init中写入对应的校准寄存器中。
                     调试时，需观察mcCurOffset结构体中对应变量是否在范围内。
    Date           : 2020-04-10
    Parameter      : None
------------------------------------------------------------------------------------------------- */
void Motor_Ready(void)
{
    if (McStaSet.SetFlag.CalibFlag == 0)
    {
        McStaSet.SetFlag.CalibFlag = 1;
        ClrBit(DRV_CR, FOCEN);
        MOE = 0;
        SetBit(ADC_MASK, CH4EN | CH2EN | CH1EN | CH0EN);
        mcCurOffset.OffsetFlag = 0;
        mcCurOffset.OffsetCount = 0;    //偏置电压采集计数
    }
}

/* -------------------------------------------------------------------------------------------------
    Function Name  : Motor_Init
    Description    : 对电机相关变量、PI进行初始化设置
    Date           : 2020-04-10
    Parameter      : None
------------------------------------------------------------------------------------------------- */
void Motor_Init(void)
{
    ClrBit(ADC_MASK, CH4EN | CH1EN | CH0EN);      // 关闭软件电流采样的ADC
    VariablesPreInit();                           // 电机相关变量初始化
    SetBit(DRV_CR, DRVEN);
}






