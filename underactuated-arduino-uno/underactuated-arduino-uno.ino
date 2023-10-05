#define PWM_MAX_DUTY 240
#define PWM_MIN_DUTY 20
#define PWM_START_DUTY 20
#define n_BLDC_cycles 7
#define PI 3.1415926535897932384626433832795
#define MAX_PITCHROLL 32767

const float full_cycle = 2 * PI;
const byte motor_step_mod = n_BLDC_cycles * 6;
const float step_angle = full_cycle / motor_step_mod;

boolean modulated_thrust_mode = false;
const int EN1 = 2;
int x = 0;
byte bldc_step = 0, motor_speed;
int motor_step = 0;
int i = 0;

float sin_comp[motor_step_mod];
float cos_comp[motor_step_mod];
void build_angle_tables()
{
  for (byte z = 0; z < motor_step_mod; z++)
  {
    const float angle = step_angle * (float)z;
    sin_comp[z] = sin(angle);
    cos_comp[z] = cos(angle);
  }
}

float n_pitch = 0.0;
float n_roll = 0.0;
byte n_duty_target = PWM_START_DUTY;
byte duty_dynamic = n_duty_target;

/*
  port B digital pin x,x,13,12,11,10,9,8
  DDRB - The Port B Data Direction Register - read/write
  PORTB - The Port B Data Register - read/write
  PINB - The Port B Input Pins Register - read only
*/

/*
  portD digital pins 7,6,5,4,3,2,1,0
  DDRD - The Port D Data Direction Register - read/write
  PORTD - The Port D Data Register - read/write
  PIND - The Port D Input Pins Register - read only
*/

boolean first = true;

const int size_of_float = sizeof(float);
struct DATA_W
{
  float roll;
  float pitch;
} axesStuct;

void read_host_profile()
{
  char thrust = Serial.read();
  Serial.readBytes((char *)&axesStuct.roll, size_of_float);
  Serial.readBytes((char *)&axesStuct.pitch, size_of_float);
  n_pitch = axesStuct.pitch;
  n_roll = axesStuct.roll;
  n_duty_target = thrust;
}

void setup()
{

  build_angle_tables();
  modulated_thrust_mode = false;
  pinMode(EN1, OUTPUT);
  digitalWrite(EN1, HIGH);
  Serial.begin(9600);

  // portD digital pins 7,6,5,4,3,2,1,0
  // port B digital pin x,x,13,12,11,10,9,8

  DDRD |= B00111000; // 0x38;           // Configure pins 3, 4 and 5 as outputs
  PORTD = B00000000; // write all zeros to enable phase pins 3, 4, 5

  DDRB |= B00001110; // 0x0E;           // Configure pins 9, 10 and 11 as outputs
  PORTB = B00110001; // write zeros to 9, 10 , 11

  // Timer1 module setting: set clock source to clkI/O / 1 (no prescaling)
  TCCR1A = 0;
  TCCR1B = 0x01;
  // Timer2 module setting: set clock source to clkI/O / 1 (no prescaling)
  TCCR2A = 0;
  TCCR2B = 0x01;

  n_duty_target = PWM_START_DUTY;
  SET_PWM_DUTY(PWM_START_DUTY); // Setup starting PWM with duty cycle = PWM_START_DUTY

  // Analog comparator setting
  ACSR = 0x10; // Disable and clear (flag bit) analog comparator interrupt

  x = 0;
}

void loop()
{

  while (Serial.available() < 8)
  {
    delay(100);
  }
  read_host_profile();
  while (x < 1)
  {
    i = 5000;

    // Motor start
    while (i > 100)
    {
      delayMicroseconds(i);
      bldc_move();
      bldc_step++;
      bldc_step %= 6;
      motor_step++;
      motor_step %= motor_step_mod;
      i = i - 20;
    }
    x++;
  }

  motor_speed = PWM_START_DUTY;
  ACSR |= 0x08; // Enable analog comparator interrupt

  ADCSRA = (0 << ADEN); // Disable the ADC module
}

ISR(ANALOG_COMP_vect)
{
  // BEMF debounce
  for (i = 0; i < 10; i++)
  {
    if (bldc_step & 1)
    {
      if (!(ACSR & 0x20))
        i -= 1;
    }
    else
    {
      if ((ACSR & 0x20))
        i -= 1;
    }
  }

  bldc_move();
  bldc_step++;
  bldc_step %= 6;
  motor_step++;
  motor_step %= motor_step_mod;
  if (Serial.available() > 8)
  {
    read_host_profile();
    if (n_duty_target < 20)
    {
      setup();
      return;
    }
    else
    {
      modulated_thrust_mode = true;
    }
  }
  else if (modulated_thrust_mode == true)
  {
    // difference between max duty and target
    byte duty_available = min(PWM_MAX_DUTY - n_duty_target, n_duty_target);

    float sin_component = sin_comp[motor_step];
    float cos_component = cos_comp[motor_step];
    // roll sine
    float sin_comp = n_roll * duty_available * sin_component;
    // pitch cos
    float cos_comp = n_pitch * duty_available * cos_component;

    // thrust
    float thrust = round(sin_comp + cos_comp + n_duty_target);
    SET_PWM_DUTY_STALL((int)thrust);
  }
}

void bldc_move()
{ // BLDC motor commutation function
  switch (bldc_step)
  {
  case 0:
    AH_BL();
    BEMF_C_RISING();
    break;
  case 1:
    AH_CL();
    BEMF_B_FALLING();
    break;
  case 2:
    BH_CL();
    BEMF_A_RISING();
    break;
  case 3:
    BH_AL();
    BEMF_C_FALLING();
    break;
  case 4:
    CH_AL();
    BEMF_B_RISING();
    break;
  case 5:
    CH_BL();
    BEMF_A_FALLING();
    break;
  }
}

void BEMF_A_RISING()
{
  ADCSRA = (0 << ADEN); // Disable the ADC module
  ADCSRB = (1 << ACME);
  ADMUX = 1; // Select analog channel 1 as comparator negative input
  ACSR |= 0x03;
}
void BEMF_A_FALLING()
{
  ADCSRA = (0 << ADEN); // Disable the ADC module
  ADCSRB = (1 << ACME);
  ADMUX = 1; // Select analog channel 1 as comparator negative input
  ACSR &= ~0x01;
}

void BEMF_B_RISING()
{
  ADCSRA = (0 << ADEN); // Disable the ADC module
  ADCSRB = (1 << ACME);
  ADMUX = 2; // Select analog channel 2 as comparator negative input
  ACSR |= 0x03;
}
void BEMF_B_FALLING()
{
  ADCSRA = (0 << ADEN); // Disable the ADC module
  ADCSRB = (1 << ACME);
  ADMUX = 2; // Select analog channel 2 as comparator negative input
  ACSR &= ~0x01;
}

void BEMF_C_RISING()
{
  ADCSRA = (0 << ADEN); // Disable the ADC module
  ADCSRB = (1 << ACME);
  ADMUX = 3; // Select analog channel 3 as comparator negative input
  ACSR |= 0x03;
}
void BEMF_C_FALLING()
{
  ADCSRA = (0 << ADEN); // Disable the ADC module
  ADCSRB = (1 << ACME);
  ADMUX = 3; // Select analog channel 3 as comparator negative input
  ACSR &= ~0x01;
}

void AH_BL()
{
  PORTB = 0x04;
  PORTD &= ~0x18;
  PORTD |= 0x20;
  TCCR1A = 0;    // Turn pin 11 (OC2A) PWM ON (pin 9 & pin 10 OFF)
  TCCR2A = 0x81; //
}
void AH_CL()
{
  PORTB = 0x02;
  PORTD &= ~0x18;
  PORTD |= 0x20;
  TCCR1A = 0;    // Turn pin 11 (OC2A) PWM ON (pin 9 & pin 10 OFF)
  TCCR2A = 0x81; //
}
void BH_CL()
{
  PORTB = 0x02;
  PORTD &= ~0x28;
  PORTD |= 0x10;
  TCCR2A = 0;    // Turn pin 10 (OC1B) PWM ON (pin 9 & pin 11 OFF)
  TCCR1A = 0x21; //
}
void BH_AL()
{
  PORTB = 0x08;
  PORTD &= ~0x28;
  PORTD |= 0x10;
  TCCR2A = 0;    // Turn pin 10 (OC1B) PWM ON (pin 9 & pin 11 OFF)
  TCCR1A = 0x21; //
}
void CH_AL()
{
  PORTB = 0x08;
  PORTD &= ~0x30;
  PORTD |= 0x08;
  TCCR2A = 0;    // Turn pin 9 (OC1A) PWM ON (pin 10 & pin 11 OFF)
  TCCR1A = 0x81; //
}
void CH_BL()
{
  PORTB = 0x04;
  PORTD &= ~0x30;
  PORTD |= 0x08;
  TCCR2A = 0;    // Turn pin 9 (OC1A) PWM ON (pin 10 & pin 11 OFF)
  TCCR1A = 0x81; //
}

int SET_PWM_DUTY(byte duty)
{
  if (duty < PWM_MIN_DUTY)
    duty = PWM_MIN_DUTY;
  if (duty > PWM_MAX_DUTY)
    duty = PWM_MAX_DUTY;
  OCR1A = duty; // Set pin 9  PWM duty cycle
  OCR1B = duty; // Set pin 10 PWM duty cycle
  OCR2A = duty; // Set pin 11 PWM duty cycle
  return duty;
}

int SET_PWM_DUTY_STALL(byte duty)
{
  OCR1A = duty; // Set pin 9  PWM duty cycle
  OCR1B = duty; // Set pin 10 PWM duty cycle
  OCR2A = duty; // Set pin 11 PWM duty cycle
  return duty;
}
