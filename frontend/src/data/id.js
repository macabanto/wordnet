export const getId = (obj) =>
  obj?._id?.$oid || obj?._id || obj?.id?.$oid || obj?.id || null;