const express = require('express');
const bodyParser = require('body-parser');
const apiRoutes = require('./routes/api');

const app = express();
const PORT = 3000;

app.use(bodyParser.json());

// Маршруты API
app.use('/api', apiRoutes);

app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
