const app = require('./index');
const PORT = 8000;
app.listen(PORT, () => {
    console.log(`Product service running on port ${PORT}`);
});
