-- CreateExtension
CREATE EXTENSION IF NOT EXISTS "vector";

-- CreateEnum
CREATE TYPE "Subject" AS ENUM ('MATH_PROFILE', 'MATH_BASE', 'PHYSICS', 'INFORMATICS');

-- CreateEnum
CREATE TYPE "ExamType" AS ENUM ('OGE', 'EGE');

-- CreateEnum
CREATE TYPE "SubscriptionPlan" AS ENUM ('FREE', 'STARTER', 'PRO', 'PREMIUM');

-- CreateEnum
CREATE TYPE "SubscriptionStatus" AS ENUM ('ACTIVE', 'CANCELED', 'EXPIRED', 'GRACE_PERIOD');

-- CreateEnum
CREATE TYPE "VerificationStatus" AS ENUM ('AUTO_PARSED', 'HUMAN_VERIFIED', 'COMMUNITY_VERIFIED', 'FLAGGED');

-- CreateEnum
CREATE TYPE "HomeworkStatus" AS ENUM ('DRAFT', 'GENERATED', 'ARCHIVED');

-- CreateEnum
CREATE TYPE "HomeworkFormat" AS ENUM ('WARMUP', 'HOMEWORK_BY_TOPIC', 'TEST', 'EGE_VARIANT', 'CUSTOM');

-- CreateEnum
CREATE TYPE "MaterialProcessingStatus" AS ENUM ('UPLOADED', 'PARSING', 'READY_FOR_REVIEW', 'CONFIRMED', 'FAILED');

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "clerkId" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "deletedAt" TIMESTAMP(3),

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Subscription" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "plan" "SubscriptionPlan" NOT NULL,
    "status" "SubscriptionStatus" NOT NULL,
    "startDate" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "endDate" TIMESTAMP(3) NOT NULL,
    "yukassaPaymentId" TEXT,
    "yukassaPaymentMethod" TEXT,
    "cancelledAt" TIMESTAMP(3),

    CONSTRAINT "Subscription_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PaymentRecord" (
    "id" TEXT NOT NULL,
    "subscriptionId" TEXT NOT NULL,
    "amount" INTEGER NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'RUB',
    "status" TEXT NOT NULL,
    "yukassaId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "paidAt" TIMESTAMP(3),

    CONSTRAINT "PaymentRecord_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Student" (
    "id" TEXT NOT NULL,
    "tutorId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "grade" INTEGER,
    "examTarget" "ExamType",
    "subject" "Subject",
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "deletedAt" TIMESTAMP(3),

    CONSTRAINT "Student_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "StudentWeakTopic" (
    "id" TEXT NOT NULL,
    "studentId" TEXT NOT NULL,
    "tagId" TEXT NOT NULL,
    "severity" INTEGER NOT NULL DEFAULT 2,
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "StudentWeakTopic_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TaskTag" (
    "id" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "path" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "subject" "Subject" NOT NULL,
    "examType" "ExamType" NOT NULL,
    "parentId" TEXT,
    "depth" INTEGER NOT NULL DEFAULT 0,
    "sortOrder" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "TaskTag_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Task" (
    "id" TEXT NOT NULL,
    "subject" "Subject" NOT NULL,
    "examType" "ExamType" NOT NULL,
    "taskNumber" INTEGER,
    "difficulty" INTEGER NOT NULL DEFAULT 3,
    "source" TEXT NOT NULL,
    "sourceMetadata" JSONB,
    "statementLatex" TEXT NOT NULL,
    "statementText" TEXT NOT NULL,
    "imageUrls" TEXT[],
    "answer" TEXT,
    "solutionLatex" TEXT,
    "solutionText" TEXT,
    "ownerId" TEXT,
    "verificationStatus" "VerificationStatus" NOT NULL DEFAULT 'AUTO_PARSED',
    "contentHash" TEXT NOT NULL,
    "flagCount" INTEGER NOT NULL DEFAULT 0,
    "embedding" vector(1536),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "deletedAt" TIMESTAMP(3),

    CONSTRAINT "Task_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TaskTagLink" (
    "id" TEXT NOT NULL,
    "taskId" TEXT NOT NULL,
    "tagId" TEXT NOT NULL,

    CONSTRAINT "TaskTagLink_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Homework" (
    "id" TEXT NOT NULL,
    "tutorId" TEXT NOT NULL,
    "studentId" TEXT,
    "title" TEXT NOT NULL,
    "format" "HomeworkFormat" NOT NULL DEFAULT 'HOMEWORK_BY_TOPIC',
    "status" "HomeworkStatus" NOT NULL DEFAULT 'DRAFT',
    "pdfUrl" TEXT,
    "pdfWithAnswersUrl" TEXT,
    "pdfGeneratedAt" TIMESTAMP(3),
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "deletedAt" TIMESTAMP(3),

    CONSTRAINT "Homework_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "HomeworkTask" (
    "id" TEXT NOT NULL,
    "homeworkId" TEXT NOT NULL,
    "taskId" TEXT NOT NULL,
    "order" INTEGER NOT NULL,

    CONSTRAINT "HomeworkTask_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Lesson" (
    "id" TEXT NOT NULL,
    "tutorId" TEXT NOT NULL,
    "studentId" TEXT NOT NULL,
    "date" TIMESTAMP(3) NOT NULL,
    "duration" INTEGER,
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "deletedAt" TIMESTAMP(3),

    CONSTRAINT "Lesson_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "LessonTopic" (
    "id" TEXT NOT NULL,
    "lessonId" TEXT NOT NULL,
    "tagId" TEXT NOT NULL,
    "needsReview" BOOLEAN NOT NULL DEFAULT false,
    "notes" TEXT,

    CONSTRAINT "LessonTopic_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "StudentPayment" (
    "id" TEXT NOT NULL,
    "tutorId" TEXT NOT NULL,
    "studentId" TEXT NOT NULL,
    "amount" INTEGER NOT NULL,
    "lessonsCount" INTEGER NOT NULL,
    "paymentDate" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "StudentPayment_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TutorMaterial" (
    "id" TEXT NOT NULL,
    "tutorId" TEXT NOT NULL,
    "originalFilename" TEXT NOT NULL,
    "s3Key" TEXT NOT NULL,
    "fileSize" INTEGER NOT NULL,
    "pageCount" INTEGER,
    "processingStatus" "MaterialProcessingStatus" NOT NULL DEFAULT 'UPLOADED',
    "extractedTasksCount" INTEGER NOT NULL DEFAULT 0,
    "confirmedTasksCount" INTEGER NOT NULL DEFAULT 0,
    "processingError" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "TutorMaterial_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_clerkId_key" ON "User"("clerkId");

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE INDEX "User_clerkId_idx" ON "User"("clerkId");

-- CreateIndex
CREATE INDEX "User_email_idx" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Subscription_userId_key" ON "Subscription"("userId");

-- CreateIndex
CREATE INDEX "Subscription_userId_idx" ON "Subscription"("userId");

-- CreateIndex
CREATE INDEX "Subscription_status_endDate_idx" ON "Subscription"("status", "endDate");

-- CreateIndex
CREATE UNIQUE INDEX "PaymentRecord_yukassaId_key" ON "PaymentRecord"("yukassaId");

-- CreateIndex
CREATE INDEX "PaymentRecord_subscriptionId_idx" ON "PaymentRecord"("subscriptionId");

-- CreateIndex
CREATE INDEX "Student_tutorId_idx" ON "Student"("tutorId");

-- CreateIndex
CREATE INDEX "StudentWeakTopic_studentId_idx" ON "StudentWeakTopic"("studentId");

-- CreateIndex
CREATE UNIQUE INDEX "StudentWeakTopic_studentId_tagId_key" ON "StudentWeakTopic"("studentId", "tagId");

-- CreateIndex
CREATE UNIQUE INDEX "TaskTag_code_key" ON "TaskTag"("code");

-- CreateIndex
CREATE UNIQUE INDEX "TaskTag_path_key" ON "TaskTag"("path");

-- CreateIndex
CREATE INDEX "TaskTag_subject_examType_idx" ON "TaskTag"("subject", "examType");

-- CreateIndex
CREATE INDEX "TaskTag_parentId_idx" ON "TaskTag"("parentId");

-- CreateIndex
CREATE INDEX "TaskTag_path_idx" ON "TaskTag"("path");

-- CreateIndex
CREATE UNIQUE INDEX "Task_contentHash_key" ON "Task"("contentHash");

-- CreateIndex
CREATE INDEX "Task_subject_examType_idx" ON "Task"("subject", "examType");

-- CreateIndex
CREATE INDEX "Task_verificationStatus_idx" ON "Task"("verificationStatus");

-- CreateIndex
CREATE INDEX "Task_ownerId_idx" ON "Task"("ownerId");

-- CreateIndex
CREATE INDEX "Task_difficulty_idx" ON "Task"("difficulty");

-- CreateIndex
CREATE INDEX "Task_taskNumber_idx" ON "Task"("taskNumber");

-- CreateIndex
CREATE INDEX "TaskTagLink_tagId_idx" ON "TaskTagLink"("tagId");

-- CreateIndex
CREATE INDEX "TaskTagLink_taskId_idx" ON "TaskTagLink"("taskId");

-- CreateIndex
CREATE UNIQUE INDEX "TaskTagLink_taskId_tagId_key" ON "TaskTagLink"("taskId", "tagId");

-- CreateIndex
CREATE INDEX "Homework_tutorId_idx" ON "Homework"("tutorId");

-- CreateIndex
CREATE INDEX "Homework_studentId_idx" ON "Homework"("studentId");

-- CreateIndex
CREATE INDEX "HomeworkTask_homeworkId_idx" ON "HomeworkTask"("homeworkId");

-- CreateIndex
CREATE UNIQUE INDEX "HomeworkTask_homeworkId_taskId_key" ON "HomeworkTask"("homeworkId", "taskId");

-- CreateIndex
CREATE UNIQUE INDEX "HomeworkTask_homeworkId_order_key" ON "HomeworkTask"("homeworkId", "order");

-- CreateIndex
CREATE INDEX "Lesson_tutorId_date_idx" ON "Lesson"("tutorId", "date");

-- CreateIndex
CREATE INDEX "Lesson_studentId_date_idx" ON "Lesson"("studentId", "date");

-- CreateIndex
CREATE UNIQUE INDEX "LessonTopic_lessonId_tagId_key" ON "LessonTopic"("lessonId", "tagId");

-- CreateIndex
CREATE INDEX "StudentPayment_tutorId_idx" ON "StudentPayment"("tutorId");

-- CreateIndex
CREATE INDEX "StudentPayment_studentId_idx" ON "StudentPayment"("studentId");

-- CreateIndex
CREATE INDEX "TutorMaterial_tutorId_idx" ON "TutorMaterial"("tutorId");

-- AddForeignKey
ALTER TABLE "Subscription" ADD CONSTRAINT "Subscription_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PaymentRecord" ADD CONSTRAINT "PaymentRecord_subscriptionId_fkey" FOREIGN KEY ("subscriptionId") REFERENCES "Subscription"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Student" ADD CONSTRAINT "Student_tutorId_fkey" FOREIGN KEY ("tutorId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "StudentWeakTopic" ADD CONSTRAINT "StudentWeakTopic_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "Student"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "StudentWeakTopic" ADD CONSTRAINT "StudentWeakTopic_tagId_fkey" FOREIGN KEY ("tagId") REFERENCES "TaskTag"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TaskTag" ADD CONSTRAINT "TaskTag_parentId_fkey" FOREIGN KEY ("parentId") REFERENCES "TaskTag"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Task" ADD CONSTRAINT "Task_ownerId_fkey" FOREIGN KEY ("ownerId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TaskTagLink" ADD CONSTRAINT "TaskTagLink_taskId_fkey" FOREIGN KEY ("taskId") REFERENCES "Task"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TaskTagLink" ADD CONSTRAINT "TaskTagLink_tagId_fkey" FOREIGN KEY ("tagId") REFERENCES "TaskTag"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Homework" ADD CONSTRAINT "Homework_tutorId_fkey" FOREIGN KEY ("tutorId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Homework" ADD CONSTRAINT "Homework_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "Student"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "HomeworkTask" ADD CONSTRAINT "HomeworkTask_homeworkId_fkey" FOREIGN KEY ("homeworkId") REFERENCES "Homework"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "HomeworkTask" ADD CONSTRAINT "HomeworkTask_taskId_fkey" FOREIGN KEY ("taskId") REFERENCES "Task"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Lesson" ADD CONSTRAINT "Lesson_tutorId_fkey" FOREIGN KEY ("tutorId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Lesson" ADD CONSTRAINT "Lesson_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "Student"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LessonTopic" ADD CONSTRAINT "LessonTopic_lessonId_fkey" FOREIGN KEY ("lessonId") REFERENCES "Lesson"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LessonTopic" ADD CONSTRAINT "LessonTopic_tagId_fkey" FOREIGN KEY ("tagId") REFERENCES "TaskTag"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "StudentPayment" ADD CONSTRAINT "StudentPayment_tutorId_fkey" FOREIGN KEY ("tutorId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "StudentPayment" ADD CONSTRAINT "StudentPayment_studentId_fkey" FOREIGN KEY ("studentId") REFERENCES "Student"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TutorMaterial" ADD CONSTRAINT "TutorMaterial_tutorId_fkey" FOREIGN KEY ("tutorId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
