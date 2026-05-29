/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ['./src/**/*.{html,ts}'],
    theme: {
        extend: {
            colors: {
                // Primary: navy from the logo (JMG)
                brand: {
                    50:  '#f0f4fa',
                    100: '#dbe5f0',
                    200: '#b8cae0',
                    300: '#8eaad0',
                    400: '#6589b8',
                    500: '#476da0',
                    600: '#345487',
                    700: '#2a4570',
                    800: '#243a5c',
                    900: '#1d3557',  // dark navy
                },
                // Accent: champagne/gold (the bar chart in the logo)
                gold: {
                    50:  '#fbf7ed',
                    100: '#f4e9cd',
                    200: '#e8d3a0',
                    300: '#dabd71',
                    400: '#c4a574',
                    500: '#b08d57',
                    600: '#946d3d',
                    700: '#735932',
                },
                // Soft cream backgrounds
                cream: {
                    50:  '#fbfaf6',
                    100: '#f4f0e6',
                    200: '#e9dfc9',
                    300: '#d8c6a3',
                },
                // Sage — for ARS prices accent
                sage: {
                    50:  '#eef2ee',
                    100: '#d9e1d9',
                    200: '#bfcdc1',
                    300: '#a0b3a3',
                    400: '#80968a',
                    500: '#6e8478',
                    600: '#586a5d',
                    700: '#48564b',
                },
                // Dusty rose accent (danger)
                blush: {
                    50:  '#f7ebe7',
                    100: '#ecd2c8',
                    200: '#dba696',
                    300: '#c47e6a',
                    400: '#a96450',
                    500: '#945242',
                },
                // Keep beige alias for backward compat
                beige: {
                    50:  '#fbf7ed',
                    100: '#f4e9cd',
                    200: '#e8d3a0',
                    300: '#dabd71',
                    400: '#c4a574',
                    500: '#b08d57',
                    600: '#946d3d',
                    700: '#735932',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
                display: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
            },
            boxShadow: {
                'soft':   '0 1px 3px rgba(29,53,87,0.08), 0 1px 2px rgba(29,53,87,0.06)',
                'lift':   '0 10px 25px -5px rgba(29,53,87,0.15), 0 8px 10px -6px rgba(29,53,87,0.08)',
                'pastel': '0 4px 16px -2px rgba(176,141,87,0.18)',
            },
            keyframes: {
                'fade-in':   { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
                'fade-out':  { '0%': { opacity: '1' }, '100%': { opacity: '0' } },
                'scale-in':  { '0%': { transform: 'scale(0.92)', opacity: '0' }, '100%': { transform: 'scale(1)', opacity: '1' } },
            },
            animation: {
                'fade-in':  'fade-in 0.6s ease-out',
                'fade-out': 'fade-out 0.5s ease-in forwards',
                'scale-in': 'scale-in 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
            },
        },
    },
    plugins: [],
};
