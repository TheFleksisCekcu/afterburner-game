#pragma once

#include <string>

struct AppOptions
{
	std::string inputFile;
	std::string outputFile;

	bool dumpHeader = false;
	bool dumpBones = false;
	bool dumpBoneControllers = false;
	bool dumpSequences = false;
};