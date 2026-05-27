import { PrismaClient, type Subject, type ExamType } from '@prisma/client';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const prisma = new PrismaClient();

type TagNode = {
  code: string;
  name: string;
  description?: string;
  children?: TagNode[];
};

type TagFile = {
  subject: Subject;
  examType: ExamType;
  rootPrefix: string;
  description?: string;
  tree: TagNode[];
};

async function seedTagTree(file: TagFile) {
  let sortCounter = 0;

  async function walk(node: TagNode, parentId: string | null, parentPath: string, depth: number) {
    const path = parentPath ? `${parentPath}.${node.code}` : `${file.rootPrefix}.${node.code}`;

    const tag = await prisma.taskTag.upsert({
      where: { code: path },
      update: {
        name: node.name,
        description: node.description,
        subject: file.subject,
        examType: file.examType,
        parentId: parentId ?? undefined,
        depth,
        sortOrder: sortCounter++,
        path,
      },
      create: {
        code: path,
        path,
        name: node.name,
        description: node.description,
        subject: file.subject,
        examType: file.examType,
        parentId: parentId ?? undefined,
        depth,
        sortOrder: sortCounter++,
      },
    });

    for (const child of node.children ?? []) {
      await walk(child, tag.id, path, depth + 1);
    }
  }

  for (const root of file.tree) {
    await walk(root, null, '', 0);
  }
}

async function main() {
  const mathEgePath = join(__dirname, 'tags_math_ege.json');
  const data = JSON.parse(readFileSync(mathEgePath, 'utf-8')) as TagFile;

  console.log(`Seeding tags for ${data.subject} / ${data.examType}…`);
  await seedTagTree(data);

  const count = await prisma.taskTag.count({
    where: { subject: data.subject, examType: data.examType },
  });
  console.log(`Done. TaskTag rows for ${data.subject}/${data.examType}: ${count}`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
