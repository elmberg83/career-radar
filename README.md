# Career Radar

Personlig jobbportal för GitHub Pages med schemalagd uppdatering av publika jobbflöden.

## Publicera (elmberg83)
1. Skapa ett **public** repository med namnet `career-radar` på GitHub.
2. Ladda upp **innehållet** i denna mapp till repositoryts rot, inklusive `.github/workflows/update.yml` (dolda mappar måste följa med). Enklast via Git på datorn eller GitHub Desktop.
3. Öppna **Settings → Pages → Build and deployment → Deploy from a branch**. Välj `main` och `/ (root)`, spara.
4. Öppna **Actions → Update jobs → Run workflow** för att hämta första annonserna. Kontrollera att Actions har tillstånd att skriva till repositoryt under **Settings → Actions → General → Workflow permissions** om commit misslyckas.
5. Portalen visas på `https://elmberg83.github.io/career-radar/` efter publicering.

## Så fungerar det
- GitHub Actions kör vardagar kl 06:00 UTC (07:00 vintertid, 08:00 sommartid i Sverige/Danmark). GitHubs schemaläggning är ungefärlig och körningar kan försenas.
- `refresh.py` hämtar från öppna flöden hos **Arbeitnow** och **Remotive**, filtrerar titlar och geografi och skriver `data/jobs.json`.
- Inga API-nycklar behövs. Jobbflödena kan ändras, begränsas eller vara otillgängliga. De täcker **inte** alla LinkedIn-, Jobindex- eller företagsannonser.
- Matchningsbetygen är **regelbaserade uppskattningar**, inte AI-bedömningar av hela annonser och CV. Svensk sammanfattning är ännu inte automatiskt genererad; textutdraget kommer från annonskällan och kan vara på engelska.
- Sparat/ansökt lagras i den aktuella webbläsaren via localStorage och synkas **inte** mellan enheter.
- För produktionsversion med bredare källor, AI-bedömning och enhetssynk behövs ytterligare integrationer och eventuellt API-nycklar/backend.

## Manuell körning
`python refresh.py` (Python 3.12+, standardbibliotek räcker).
