/*  --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : main.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-10
    Description    : This file contains .C file function used for Motor Control.
    ----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
    ------------------------------------------------------------------------------------------------- */
/********************************************************************************
    Header Definition
********************************************************************************/
#include <MyProject.h>

/********************************************************************************
    Internal Routine Prototypes
********************************************************************************/
void HardwareInit(void);
void SoftwareInit(void);
void VREFConfigInit(void);
uint8 SYST_Times;
/********************************************************************************
    Macro & Structure Definition
********************************************************************************/



/********************************************************************************
    Function Definition
********************************************************************************/
/*  -------------------------------------------------------------------------------------------------
        Function Name : void DebugSet(void)
        Description   : 调试模式配置
        Input         : 无
        Output        : 无
    -------------------------------------------------------------------------------------------------*/
typedef struct
{
    uint8   Length;
    uint8   CheckSum;
    uint8   T_DATA[20];
} TypeDef_UartANO;

void DebugSet(void)
{
    #if (DBG_MODE == SPI_DBG_HW)        // 硬件调试模式
    {
        SPI_Init();
        Set_DBG_DMA(&HARD_SPIDATA);
    }
    #elif (DBG_MODE == SPI_DBG_SW)      // 软件调试模式
    {
        SPI_Init();
        Set_DBG_DMA(spidebug);
    }
    #elif (DBG_MODE == UART_DBG)        // UART调试模式
    {
//        UART2_Init();
				UART1_Init();
        SetPipe_DMA0(DRAM_UART2);
    }
    #endif
}


/*  -------------------------------------------------------------------------------------------------
    Function Name  : HardwareInit
    Description    : 硬件初始化，初始化需要使用的硬件设备配置，FOC必须配置的是运放电压、运放初始化、ADC初始化、Driver初始化
                    ，其他的可根据实际需求加。
    Date           : 2020-04-12
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */
void HardwareInit(void)
{
    // 为提高芯片的抗干扰能力，降低芯片功耗，请在具体项目时，将不需要用的GPIO默认都配置为输入上拉。
    // 具体配置可在GPIO_Default_Init设置。
    // GPIO_Default_Init();
    /*********硬件过流，比较器初始化，用于硬件过流比较保护*********/
    CMP3_Init();
    GPIO_Init();
    EXTI_Init();
    Driver_Init();
    //  TIM1_HALL_Init();
    Timer2_QEP_Init();
    Timer3_Init();
    VREFConfigInit();  /* ADC参考电压电压配置 */
    ADC_Init();
    AMP_Init();
    /* -----比较器中断配置----- */
    CMP3_Interrupt_Init();
    //Timer4_Init();
    /* -----SYSTICK定时器配置----- */
    SYST_ARR = 12000;   //4000
    //    SYST_Times  = MCU_CLOCK * (1000000 / 6000) / 1000;
    SYST_Times  = MCU_CLOCK / (12000 / 1000.0);
    SetBit(DRV_SR, SYSTIE);
    //    ClrBit(P2_OE, P26);                       /* 0: Disable digital output */
    //    ClrBit(P2_PU, P26);                       /* 0: Disable internal pull up */
}

/*  -------------------------------------------------------------------------------------------------
    Function Name  : SoftwareInit
    Description    : 软件初始化，初始化所有定义变量，按键初始化扫描
    Date           : 2020-04-12
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */
void SoftwareInit(void)
{
    MotorcontrolInit();
    PI_Init();
    mcState       = mcReady;
    mcFaultSource = 0;
}

/*  -------------------------------------------------------------------------------------------------
    Function Name  : VREFConfigInit
    Description    : 配置VREF/VHALF输出
    Date           : 2020-04-12
    Parameter      : None
    ------------------------------------------------------------------------------------------------- */
float Vofa_Data[7] = {0};
TypeDef_UartANO     xdata UART_ANO;

void Float2Char(float * DataTemp, uint8 * P, uint8 length) //适配Vofa上位机
{
    unsigned char j  = 0;
    
    for (j = 0; j < length; j++)
    {
        P[(j << 2) + 3] = *((uint8 *)(DataTemp + j));
        P[(j << 2) + 2] = *((uint8 *)(DataTemp + j) + 1);
        P[(j << 2) + 1] = *((uint8 *)(DataTemp + j) + 2);
        P[(j << 2)] = *((uint8 *)(DataTemp + j) + 3);
    }
}

void Vofa_SendData(float * VofaData, uint8 length)
{
    /*************发送数据*************************/
    memcpy(UART_ANO.T_DATA, (uint8 *)VofaData, ((length << 2))); //通过拷贝把数据重新整理 这个要小端对齐
    Float2Char(VofaData, UART_ANO.T_DATA, length); //小端调整为大端
    UART_ANO.T_DATA[(length << 2)] = 0x00;          //写如结尾数据
    UART_ANO.T_DATA[(length << 2) + 1] = 0x00;
    UART_ANO.T_DATA[(length << 2) + 2] = 0x80;
    UART_ANO.T_DATA[(length << 2) + 3] = 0x7f;
}

void VREFConfigInit(void)
{
    /* ***********************VREF&VHALF Config*********************** */
    ClrBit(P3_AN, PIN5);                         //VREF Voltage -->P35 Output 是否输出到P35引脚
    
    if (HW_ADC_REF == 3.0)
    {
        SetBit(VREF_VHALF_CR, VRVSEL1);             //00-->4.5V   01-->VDD5
        ClrBit(VREF_VHALF_CR, VRVSEL0);             //10-->3.0V   11-->4.0V
    }
    else if (HW_ADC_REF == 4.0)
    {
        SetBit(VREF_VHALF_CR, VRVSEL1);             //00-->4.5V   01-->VDD5
        SetBit(VREF_VHALF_CR, VRVSEL0);             //10-->3.0V   11-->4.0V
    }
    else if (HW_ADC_REF == 4.5)
    {
        ClrBit(VREF_VHALF_CR, VRVSEL1);             //00-->4.5V   01-->VDD5
        ClrBit(VREF_VHALF_CR, VRVSEL0);             //10-->3.0V   11-->4.0V
    }
    else
    {
        ClrBit(VREF_VHALF_CR, VRVSEL1);             //00-->4.5V   01-->VDD5
        SetBit(VREF_VHALF_CR, VRVSEL0);             //10-->3.0V   11-->4.0V
    }
    
    SetBit(VREF_VHALF_CR, VREFEN | VHALFEN);    //VREF_VHALF_CR = 0x11;
}

void UART1_Init_Debuger(void)
{
    SetBit(PH_SEL, UART1EN);    // P0[6]as UART2_RXD; P0[5]as UART2_TXD
    UT_MOD1 = 0;                // 8bit波特率可变UART模式
    UT_MOD0 = 1;
    SM2     = 0;                //
    REN     = 1;                // 使能接收
    ES0 = 0;                    // 发送/接受中断使能
    UT_BAUD = 0x000c;           // 9B-->9600 0x000c-->115200 0x0005-->256000 0x0006-->250000
}

//void DMA1_XRAMToUART_Init(uint16 Addr,uint8 Length)
//{
//    SetReg(DMA1_CR0, DMAEN | DMACFG2 | DMACFG1 | DMACFG0 | DMAIE, DMACFG0);
//      DMA1_LEN = Length-1;                                // 设置DMA1发送数量为8
//    DMA1_BA = Addr & 0x07ff;                            // 设置DMA1发送首地址
//    Switch_DMA(1);                                      // 启动DMA1
//}

uint8 cnt = 0;
void DMA1_XRAMToUART_Init(uint16 Addr, uint8 Length)
{
    SetReg(DMA1_CR0, DMAEN | DMACFG2 | DMACFG1 | DMACFG0 | DMAIE, DMACFG2 | DMACFG1 | DMACFG0);
    DMA1_LEN = Length - 1;                              // 设置DMA1发送数量为8
    DMA1_BA = Addr & 0x07ff;                            // 设置DMA1发送首地址
    Switch_DMA(1);                                      // 启动DMA1
}

extern int32  PosErr;
extern int32  speedRef;
extern int32  speedErr;
extern int16  t1;

void main(void)
{
    uint16 PowerUpCnt = 0;
    
    /*********上电等待*********/
    for (PowerUpCnt = 0; PowerUpCnt < SystemPowerUpTime; PowerUpCnt++);
    
    HardwareInit();  /* Hardware & Software Initial */
    SoftwareInit();
    DebugSet();
    #if (REF_MODE == UARTMODE)
    UART2_Init();
    SetPipe_DMA0(DRAM_UART2);
    #endif
    EA = 1;
		memset(&UqPo,0,sizeof(UQ_Posi));
		UqPo.UqPosiLockFlag = 1;//用dq电压锁轴的标志位，1表示可以锁轴，0表示已经锁轴了
    isCtrlPowerOn = true;
    Speed_Handle(0x79);
	//DMA1_XRAMToUART_Init(Uart.T_DATA, 20); //
    while (1)
    {
            
        /* -----Current calibration----- */
        GetCurrentOffset();
        /* -----Motor Control State----- */
        MC_Control();
        

        if (!Learn.FilishFlag)
        {
						UartDealComm();
            Self_Learning(); //Z信号自学习
        }
        
				if (Learn.State == LearnOver)
        {            
			  UartDealComm2();
        }
			   
			

        #if 0 //打开串口会影响上电动作
				if((mcQEP.g1msflg >= 10)&&(Learn.FilishFlag))
				{
					mcQEP.g1msflg = 0;
					Wait_DMA(1);
					Vofa_Data[0] = PosErr;
					Vofa_Data[1] = speedErr;//mcQEP.AbsSpeed ;//mcQEP.CntrSum;
					Vofa_Data[2] = FOC_IQREF ; //
					Vofa_Data[3] = mcQEP.SpeedMFlt;//mcQEP.Cntr&0X00FF;//
					Vofa_SendData(Vofa_Data, 4);
					Switch_DMA(1);
				}
        #endif
    }
}