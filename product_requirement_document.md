# Automation Simon

Status: In progress

**Objective**:

1. Retrieve the latest monthly report for each fund (examples shared in the table below for November)
    - Carmignac → the data is already available on the website but a 2-steps modal is displayed to confirm data usage + confirm investor profil (pro)
        
        
        [https://www.notion.so](https://www.notion.so)
        
        ![Screenshot 2025-11-28 at 16.25.30.png](Automation%20Simon/Screenshot_2025-11-28_at_16.25.30.png)
        
    - Sycomore → Have to config my investor profile (CGP / Particulier) + France
        
        ![Screenshot 2025-11-28 at 16.26.09.png](Automation%20Simon/Screenshot_2025-11-28_at_16.26.09.png)
        
        ![Screenshot 2025-11-28 at 16.26.35.png](Automation%20Simon/Screenshot_2025-11-28_at_16.26.35.png)
        
        ![Screenshot 2025-11-28 at 16.26.43.png](Automation%20Simon/Screenshot_2025-11-28_at_16.26.43.png)
        
    - Rotschild → Have a modal asking for the country (France)+ and profile (Professional) + checkbox to acknowledge the above informations, then the “monthly report” is stored in a section called “reporting” (there is a dropdown listing the months, I want the latest)
        
        ![Screenshot 2025-11-29 at 09.54.15.png](Automation%20Simon/Screenshot_2025-11-29_at_09.54.15.png)
        
        ![Screenshot 2025-11-28 at 16.28.22.png](Automation%20Simon/Screenshot_2025-11-28_at_16.28.22.png)
        
2. Extract Yield to maturity / Rendement à maturité (e.g. 4,9%)
3. Store each value for each target‑maturity bond mutual fund
4. Create a dot graph with the duration in abscisses and Yield to maturity in ordonnée

The app we’ll be triggered once a month to fetch the new data, Thus displaying multiple graphs and a table of the data used for each graph. 

[Untitled](Automation%20Simon/Untitled%202b9271b2609680bdbfa7d8d5cf6f45d3.csv)

- **Results for Evals**:
    
    
    | Fonds | maturité | rendement actuariel | notation moyenne |
    | --- | --- | --- | --- |
    | Tikehau 2027 | 2027 | 4.10% | BB |
    | Tikehau 2029 | 2029 | 3.30% | BBB+ |
    | Carmignac crédit 2027 | 2027 | 3.90% | A- |
    | Carmignac crédit 2029 | 2029 | 4.60% | BBB+ |
    | Carmignac crédit 2031 | 2031 | 5.10% | BBB- |
    | Sycoyield 2030 | 2030 | 4.90% | BB- |
    | Sycoyield 2032 | 2032 | 4.90% | BB- |
    | R-co Target 2028 IG | 2028 | 2.85% | BBB |
    | R-co Target 2029 IG | 2029 | 3.06% | BBB |
    | R-co Target 2030 IG | 2030 | 3.31% | BBB |