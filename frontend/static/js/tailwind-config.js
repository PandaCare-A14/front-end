tailwind.config = {
    theme: {
        extend: {
            colors: {
                primary: {
                    DEFAULT: '#1A76D2',
                    '80': '#1A76D2CC',
                    '60': '#1A76D299',
                    '40': '#1A76D266',
                    '20': '#1A76D233',
                },
                secondary: {
                    DEFAULT: '#E8F1FC',
                    '80': '#E8F1FCCC',
                    '60': '#E8F1FC99',
                    '40': '#E8F1FC66',
                    '20': '#E8F1FC33',
                },
                accent: {
                    '50': '#F0F7FF',
                    '200': '#D4E5F9',
                    '400': '#82B5ED',
                    '500': '#0D5CAB',
                    '600': '#094A8C',
                    '700': '#073A70',
                    '800': '#052C55',
                },
                popover: {
                    DEFAULT: "hsl(var(--popover))",
                    foreground: "hsl(var(--popover-foreground))",
                },
                card: {
                    DEFAULT: "hsl(var(--card))",
                    foreground: "hsl(var(--card-foreground))",
                },
                neutral: {
                    'black': '#121212',
                    'white': '#FFFFFF'
                }
            },
            fontFamily: {
                'header': ['Montserrat', 'Helvetica', 'Arial', 'sans-serif'],
                'body': ['Poppins', 'sans-serif']
            },
            fontSize: {
                'h1': ['48px', { lineHeight: 'normal', fontWeight: '700' }],
                'h2': ['36px', { lineHeight: 'normal', fontWeight: '700' }],
                'h3': ['30px', { lineHeight: 'normal', fontWeight: '700' }],
                'h4': ['24px', { lineHeight: 'normal', fontWeight: '700' }],
                'h5': ['20px', { lineHeight: 'normal', fontWeight: '700' }],
                'h6': ['18px', { lineHeight: '140%', fontWeight: '700' }]
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            keyframes: {
                "accordion-down": {
                    from: { height: "0" },
                    to: { height: "var(--radix-accordion-content-height)" },
                },
                "accordion-up": {
                    from: { height: "var(--radix-accordion-content-height)" },
                    to: { height: "0" },
                }
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
            }
        }
    },
    variants: {
        extend: {
            backgroundColor: ['hover', 'active', 'focus'],
            textColor: ['hover', 'active', 'focus'],
            borderColor: ['hover', 'active', 'focus'],
            opacity: ['hover', 'active', 'focus']
        }
    }
};