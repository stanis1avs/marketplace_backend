const Koa = require('koa');
const Router = require('koa-router');
const cors = require('koa2-cors');
const koaBody = require('koa-body');
const { Pool } = require('pg');
const dotenv = require('dotenv').config();

const port = process.env.PORT || 7070;;
const topSaleIds = [66, 65, 73];
const moreCount = 6;

const pool = new Pool({
  connectionString: process.env.POSTGRES_URL,
  ssl: {
    rejectUnauthorized: false,
  }
});

const server = new Koa();
server.use(cors());
server.use(koaBody({
    json: true
}));

const router = new Router();

const queryDatabase = async(query, params) => {
  const client = await pool.connect();
  try {
    const res = await client.query(query, params);
    return res.rows;
  } finally {
    client.release();
  }
}

const randomNumber = (start, stop) => {
  return Math.floor(Math.random() * (stop - start + 1)) + start;
}

const fortune = (ctx, body = null, status = 200) => {
  //const delay = randomNumber(1, 10) * 1000;
  const delay = 0;
  return new Promise((resolve, reject) => {
      setTimeout(() => {
          // if (Math.random() > 0.8) {
          //     reject(new Error('Something bad happened'));
          //     return;
          // }
          ctx.response.status = status;
          ctx.response.body = body;
          resolve();
      }, delay);
  })
}

router.get('/api/top-sales', async (ctx, next) => {
  const topSales = await queryDatabase(`
    SELECT id, title, price, images
    FROM products
    WHERE id IN (${topSaleIds.join()})`);
  return fortune(ctx, topSales);
});

router.get('/api/categories', async (ctx, next) => {
  const categories = await queryDatabase('SELECT * FROM categories');
  return fortune(ctx, categories);
});

router.get('/api/items', async (ctx, next) => {
  const { query } = ctx.request;

  const q = query.q ? `%${query.q.trim().toLowerCase()}%` : '';
  const categoryId = query.categoryId ? Number(query.categoryId) : 0;
  const offset = query.offset ? Number(query.offset) : 0;

  const sql = `
    SELECT id, category, title, price, images
    FROM products
    WHERE  ($1 = '' OR LOWER(title) LIKE $1 OR LOWER(color) LIKE $1)
    AND ($2 = 0 OR category = $2)
    LIMIT ${moreCount} OFFSET $3;
  `;

  const items = await queryDatabase(sql, [q, categoryId, offset]);
  return fortune(ctx, items);
});

router.get('/api/items/:id', async (ctx, next) => {
  const item = await queryDatabase(`
    SELECT products.*, array_agg(json_build_object('size', sizes.size, 'available', sizes.avalible)) as sizes
    FROM products
    JOIN sizes ON products.id = sizes.productid
    WHERE ${ctx.params.id} = products.id
    GROUP BY products.id;`);
  if (!item) {
    return fortune(ctx, 'Not found', 404);
  }
  return fortune(ctx, item[0]);
});

router.post('/api/order', async (ctx, next) => {
  const { owner: { phone, address }, items } = ctx.request.body;
  if (typeof phone !== 'string') {
      return fortune(ctx, 'Bad Request: Phone', 400);
  }
  if (typeof address !== 'string') {
      return fortune(ctx, 'Bad Request: Address', 400);
  }
  if (!Array.isArray(items)) {
      return fortune(ctx, 'Bad Request: Items', 400);
  }
  if (!items.every(({ id, price, count }) => {
      if (typeof id !== 'number' || id <= 0) {
          return false;
      }
      if (typeof price !== 'number' || price <= 0) {
          return false;
      }
      if (typeof count !== 'number' || count <= 0) {
          return false;
      }
      return true;
  })) {
      return fortune(ctx, 'Bad Request', 400);
  }
  return fortune(ctx, null, 204);
});


server.use(router.routes())
server.use(router.allowedMethods());

server.listen(port);